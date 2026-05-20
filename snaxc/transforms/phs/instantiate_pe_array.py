from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.dialects.builtin import DenseArrayBase, IntegerType
from xdsl.dialects.linalg.attrs import IteratorType
from xdsl.dialects.linalg.ops import GenericOp as LinalgGenericOp
from xdsl.ir.affine import AffineConstantExpr, AffineDimExpr, AffineExpr, AffineMap
from xdsl.parser import SymbolRefAttr
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter, PatternRewriteWalker, RewritePattern, op_type_rewrite_pattern
from xdsl.rewriter import InsertPoint
from xdsl.utils.hints import isa

from snaxc.dialects import phs
from snaxc.phs.instantiate_array import build_pe_array_body
from snaxc.phs.template_spec import TemplateSpec

BOUNDS_ATTR_NAME = "phs_array_bounds"
PAIRED_OUTPUTS_ATTR_NAME = "phs.paired_outputs"
MAGIC_ATTR_NAME = "phs_acc"


def _dense_ints(attr: DenseArrayBase[IntegerType]) -> tuple[int, ...]:
    return tuple(int(v) for v in attr.get_values())


def _project_to_parallel(affine_map: AffineMap, parallel_dims: tuple[int, ...]) -> AffineMap:
    """
    Restrict an affine map to a subset of its iteration dims (the parallel ones).

    Result expressions referencing any non-parallel dim are dropped (they describe
    the temporal access pattern that the streamer handles, not the per-PE spatial
    access pattern). Remaining domain dims are renumbered contiguously so the
    map's num_dims equals len(parallel_dims).
    """
    parallel_set = set(parallel_dims)
    new_dims: list[AffineExpr] = []
    for d in range(affine_map.num_dims):
        if d in parallel_set:
            new_dims.append(AffineDimExpr(parallel_dims.index(d)))
        else:
            new_dims.append(AffineConstantExpr(0))

    new_results: list[AffineExpr] = []
    for expr in affine_map.results:
        if all(d in parallel_set for d in expr.used_dims()):
            new_results.append(expr.replace_dims_and_symbols(new_dims, []))

    return AffineMap(len(parallel_dims), 0, tuple(new_results))


def _collect_modes_from_linalg(
    pe: phs.PEOp, module: builtin.ModuleOp, paired_outputs: tuple[int, ...]
) -> list[tuple[tuple[AffineMap, ...], tuple[AffineMap, ...], tuple[int, ...]]]:
    """
    Walk the module for linalg.generics tagged with phs_acc == pe.sym_name.
    Each match becomes one dataflow mode of the resulting pe_array.

    input_maps for the resulting mode are built as:
        pure_inputs (from linalg ins=) + carry_inputs (mirror of paired output maps)
    matching the encode-pass convention that the PE block-arg ordering is
    [pure-input-args..., carry-input-args...].
    """
    pe_name = pe.name_prop.data
    modes: list[tuple[tuple[AffineMap, ...], tuple[AffineMap, ...], tuple[int, ...]]] = []
    for op in module.walk():
        if not isinstance(op, LinalgGenericOp):
            continue
        acc = op.attributes.get(MAGIC_ATTR_NAME)
        if not isinstance(acc, SymbolRefAttr) or acc.string_value() != pe_name:
            continue
        num_ins = len(op.inputs)
        raw_pure_in_maps = tuple(m.data for m in op.indexing_maps.data[:num_ins])
        raw_out_maps = tuple(m.data for m in op.indexing_maps.data[num_ins:])

        # The linalg indexing_maps cover the full iteration space (parallel +
        # reduction). phs_array_bounds counts only the spatial (parallel) dims
        # the PE array unrolls; the streamer cycles the temporal/reduction
        # dims. Project the maps onto the parallel-dim subset.
        parallel_dims = tuple(
            i for i, it in enumerate(op.iterator_types.data) if it.data == IteratorType.PARALLEL
        )
        pure_in_maps = tuple(_project_to_parallel(m, parallel_dims) for m in raw_pure_in_maps)
        out_maps = tuple(_project_to_parallel(m, parallel_dims) for m in raw_out_maps)
        carry_in_maps = tuple(out_maps[k] for k in paired_outputs)
        in_maps = pure_in_maps + carry_in_maps

        bounds_attr_lin = op.attributes.get(BOUNDS_ATTR_NAME)
        if not isa(bounds_attr_lin, DenseArrayBase[IntegerType]):
            continue
        bounds = _dense_ints(bounds_attr_lin)
        assert len(bounds) == len(parallel_dims), (
            f"phs_array_bounds {bounds} count {len(bounds)} != #parallel iterator dims "
            f"{len(parallel_dims)} on linalg.generic for @{pe_name}"
        )
        modes.append((in_maps, out_maps, bounds))
    return modes


def _compute_paired_outputs(pe: phs.PEOp, module: builtin.ModuleOp | None) -> tuple[int, ...]:
    """Resolve carry→output pairing from PE attribute, or infer from PE arity."""
    paired_attr = pe.attributes.get(PAIRED_OUTPUTS_ATTR_NAME)
    if isa(paired_attr, DenseArrayBase[IntegerType]):
        return _dense_ints(paired_attr)
    # Infer: carry count = PE data operands - #linalg pure inputs. Default 0
    # carries when no linalg source is available.
    pe_data = len(pe.data_operands())
    pe_name = pe.name_prop.data
    if module is not None:
        for op in module.walk():
            if isinstance(op, LinalgGenericOp):
                acc = op.attributes.get(MAGIC_ATTR_NAME)
                if isinstance(acc, SymbolRefAttr) and acc.string_value() == pe_name:
                    carries = max(0, pe_data - len(op.inputs))
                    return tuple(range(carries))
    return ()


@dataclass(frozen=True)
class InstantiatePEArrays(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, pe: phs.PEOp, rewriter: PatternRewriter):
        toplevel = pe.get_toplevel_object()
        module = toplevel if isinstance(toplevel, builtin.ModuleOp) else None

        paired_outputs = _compute_paired_outputs(pe, module)

        modes: list[tuple[tuple[AffineMap, ...], tuple[AffineMap, ...], tuple[int, ...]]] = []
        if module is not None:
            modes = _collect_modes_from_linalg(pe, module, paired_outputs)

        # Fall back to PE-attached bounds + identity maps when no linalg sources exist.
        if not modes:
            if BOUNDS_ATTR_NAME not in pe.attributes:
                return
            bounds_attr = pe.attributes[BOUNDS_ATTR_NAME]
            assert isa(bounds_attr, DenseArrayBase[IntegerType])
            pe_bounds = _dense_ints(bounds_attr)
            num_data = len(pe.data_operands())
            num_outputs = len(pe.get_terminator().operands)
            num_dims = len(pe_bounds)
            id_in = tuple(AffineMap.identity(num_dims) for _ in range(num_data))
            id_out = tuple(AffineMap.identity(num_dims) for _ in range(num_outputs))
            modes = [(id_in, id_out, pe_bounds)]

        # Bounds must agree across modes.
        bounds = modes[0][2]
        for _, _, b in modes:
            assert b == bounds, f"All modes must share bounds; got {b} vs {bounds}"

        num_data = len(pe.data_operands())
        num_pure_inputs = num_data - len(paired_outputs)

        # Body wiring uses mode 0 as the canonical mode.
        in_maps_0, out_maps_0, _ = modes[0]
        template_spec = TemplateSpec(
            input_maps=in_maps_0,
            output_maps=out_maps_0,
            template_bounds=bounds,
            paired_outputs=paired_outputs,
        )
        array_op = build_pe_array_body(
            pe,
            template_spec,
            pe_ref=pe.name_prop.data,
            bounds=bounds,
            num_pure_inputs=num_pure_inputs,
            paired_outputs=paired_outputs,
            input_modes=[m[0] for m in modes],
            output_modes=[m[1] for m in modes],
        )
        rewriter.insert_op(array_op, InsertPoint.after(pe))

        if BOUNDS_ATTR_NAME in pe.attributes:
            del pe.attributes[BOUNDS_ATTR_NAME]


@dataclass(frozen=True)
class InstantiatePEArrayPass(ModulePass):
    name = "instantiate-pe-array"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        PatternRewriteWalker(InstantiatePEArrays(), apply_recursively=False).rewrite_module(op)

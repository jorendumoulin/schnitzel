from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.dialects.linalg.ops import GenericOp as LinalgGenericOp
from xdsl.ir import Attribute
from xdsl.ir.affine import AffineMap
from xdsl.parser import SymbolRefAttr
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter, PatternRewriteWalker, RewritePattern, op_type_rewrite_pattern
from xdsl.rewriter import InsertPoint

from snaxc.dialects import phs
from snaxc.phs.instantiate_array import build_pe_array_body
from snaxc.phs.template_spec import TemplateSpec

BOUNDS_ATTR_NAME = "phs_array_bounds"
PAIRED_OUTPUTS_ATTR_NAME = "phs.paired_outputs"
MAGIC_ATTR_NAME = "phs_acc"


def _dense_ints(attr: Attribute) -> tuple[int, ...]:
    assert isinstance(attr, builtin.DenseArrayBase)
    return tuple(int(v) for v in attr.get_values())  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType,reportUnknownArgumentType]


def _collect_modes_from_linalg(
    pe: phs.PEOp, module: builtin.ModuleOp
) -> list[tuple[tuple[AffineMap, ...], tuple[AffineMap, ...], tuple[int, ...]]]:
    """
    Walk the module for linalg.generics tagged with phs_acc == pe.sym_name.
    Each match becomes one dataflow mode of the resulting pe_array.
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
        in_maps = tuple(m.data for m in op.indexing_maps.data[:num_ins])
        out_maps = tuple(m.data for m in op.indexing_maps.data[num_ins:])

        bounds_attr_lin = op.attributes.get(BOUNDS_ATTR_NAME)
        if not isinstance(bounds_attr_lin, builtin.DenseArrayBase):
            continue
        bounds = _dense_ints(bounds_attr_lin)  # pyright: ignore[reportUnknownArgumentType]
        modes.append((in_maps, out_maps, bounds))
    return modes


@dataclass(frozen=True)
class InstantiatePEArrays(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, pe: phs.PEOp, rewriter: PatternRewriter):
        # Try to collect modes from the originating linalg.generics first.
        toplevel = pe.get_toplevel_object()
        modes: list[tuple[tuple[AffineMap, ...], tuple[AffineMap, ...], tuple[int, ...]]] = []
        if isinstance(toplevel, builtin.ModuleOp):
            modes = _collect_modes_from_linalg(pe, toplevel)

        # Fall back to PE-attached bounds + identity maps when no linalg sources exist.
        if not modes:
            if BOUNDS_ATTR_NAME not in pe.attributes:
                return
            bounds_attr = pe.attributes[BOUNDS_ATTR_NAME]
            assert isinstance(bounds_attr, builtin.DenseArrayBase)
            pe_bounds = _dense_ints(bounds_attr)  # pyright: ignore[reportUnknownArgumentType]
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

        # paired_outputs from the PE attribute (encode pass + prune pass).
        paired_attr = pe.attributes.get(PAIRED_OUTPUTS_ATTR_NAME)
        if paired_attr is None:
            paired_outputs = tuple(range(min(len(modes[0][1]), len(modes[0][0]))))
        else:
            assert isinstance(paired_attr, builtin.DenseArrayBase)
            paired_outputs = _dense_ints(paired_attr)  # pyright: ignore[reportUnknownArgumentType]

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

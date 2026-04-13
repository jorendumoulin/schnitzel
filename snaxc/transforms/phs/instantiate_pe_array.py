from dataclasses import dataclass
from typing import cast

from xdsl.context import Context
from xdsl.dialects import builtin, hw
from xdsl.ir import Attribute, Block, Region, SSAValue
from xdsl.ir.affine import AffineMap
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter, PatternRewriteWalker, RewritePattern, op_type_rewrite_pattern
from xdsl.rewriter import InsertPoint
from xdsl.utils.hints import isa

from snaxc.dialects import phs
from snaxc.phs.hw_conversion import (
    create_shaped_hw_array,
    create_shaped_hw_array_type,
    get_from_shaped_hw_array,
)
from snaxc.phs.template_spec import TemplateSpec


def _build_pe_array_body(
    pe: phs.PEOp,
    template_spec: TemplateSpec,
) -> phs.PEArrayOp:
    """
    Build a PEArrayOp with explicit wiring derived from the TemplateSpec maps.

    For each PE data input, the corresponding input_map determines connectivity:
    - Map produces non-empty shape: input comes from an array, indexed per iteration.
    - Map produces empty shape: input is scalar — a **chain** candidate.

    For outputs, the output_map shape determines the result structure:
    - Full shape (== bounds): fully parallel, each PE produces one output element.
    - Empty shape: fully reduced, scalar output from last PE in chain.
    - Partial shape (< bounds): partially reduced. PEs are grouped by output index;
      within each group the accumulator chains, and the group results are collected
      into the output array.

    For chained inputs, PEs that map to the same output index form a reduction group.
    The first PE in each group gets the initial value from a block arg; subsequent PEs
    get the previous PE's output within their group.
    """
    input_sizes = template_spec.get_input_sizes()
    output_sizes = template_spec.get_output_sizes()

    data_operands = pe.data_operands()
    switches = pe.get_switches()
    yield_op = pe.get_terminator()
    pe_result_types = list(yield_op.operand_types)

    # Classify inputs: chained (scalar map) vs parallel (array map)
    chained_inputs: list[int] = []  # ordered list of PE data input indices that are chained
    for i, input_size in enumerate(input_sizes):
        if len(input_size) == 0:
            chained_inputs.append(i)

    # Classify outputs by comparing output shape to bounds
    # - same as bounds: fully parallel
    # - empty: fully reduced (scalar)
    # - in between: partially reduced
    reduced_outputs: list[int] = []  # ordered list of PE result indices that are reduced
    parallel_outputs: list[int] = []
    for j, output_size in enumerate(output_sizes):
        if output_size != template_spec.template_bounds:
            reduced_outputs.append(j)
        else:
            parallel_outputs.append(j)

    # Pair chained inputs with reduced outputs in order of appearance.
    # E.g. if chained inputs are [2, 4] and reduced outputs are [0, 1],
    # then input 2 chains with output 0, input 4 chains with output 1.
    chain_pairs: list[tuple[int, int]] = list(zip(chained_inputs, reduced_outputs, strict=False))
    # Build lookup: chained input index -> which PE result index it chains from
    input_to_output_chain: dict[int, int] = {inp: out for inp, out in chain_pairs}

    # Build input types for the array block args
    in_types: list[Attribute] = []
    parallel_arg_indices: dict[int, int] = {}  # pe_data_idx -> block_arg_idx
    chained_arg_indices: dict[int, int] = {}  # pe_data_idx -> block_arg_idx

    for i, data_opnd in enumerate(data_operands):
        assert isa(data_opnd.type, builtin.AnySignlessIntegerType)
        if i in input_to_output_chain:
            chained_arg_indices[i] = len(in_types)
            in_types.append(cast(Attribute, data_opnd.type))
        else:
            parallel_arg_indices[i] = len(in_types)
            in_types.append(create_shaped_hw_array_type(data_opnd.type, input_sizes[i]))

    for _ in switches:
        in_types.append(builtin.IndexType())

    # Build output types
    out_types: list[Attribute] = []
    for j in range(len(pe_result_types)):
        out_size = output_sizes[j]
        if len(out_size) == 0:
            out_types.append(pe_result_types[j])
        else:
            el_type = yield_op.operands[j].type
            assert isa(el_type, builtin.AnySignlessIntegerType)
            out_types.append(cast(Attribute, create_shaped_hw_array_type(el_type, out_size)))

    # Create block
    import itertools

    block = Block(arg_types=in_types)
    switch_args = list(block.args[len(in_types) - len(switches) :])

    # Per-chain state: for each reduced output j, track the last PE output
    # per group key. Each chain has its own grouping based on its own output map.
    # chain_state[out_j][group_key] = last PE output for that chain in that group
    chain_state: dict[int, dict[tuple[int, ...], SSAValue]] = {out_j: {} for out_j in reduced_outputs}

    # For parallel outputs, collect all PE outputs in iteration order
    parallel_pe_outputs: dict[int, list[SSAValue]] = {j: [] for j in parallel_outputs}

    for indexes in template_spec.get_iterations():
        instance_data_operands: list[SSAValue] = []

        for i in range(len(data_operands)):
            if i in input_to_output_chain:
                # Chained input: look up the paired output's chain state
                paired_output = input_to_output_chain[i]
                group_key = template_spec.output_maps[paired_output].eval(indexes, ())
                prev = chain_state[paired_output].get(group_key)
                if prev is None:
                    # First PE in this group for this chain: use initial value
                    instance_data_operands.append(block.args[chained_arg_indices[i]])
                else:
                    # Continue chain from previous PE in this group
                    instance_data_operands.append(prev)
            else:
                # Parallel: index into array
                arg_idx = parallel_arg_indices[i]
                input_indexes = template_spec.input_maps[i].eval(indexes, ())
                array_val = SSAValue.get(block.args[arg_idx], type=hw.ArrayType)
                indexing_ops, val = get_from_shaped_hw_array(array_val, input_indexes)
                block.add_ops(indexing_ops)
                instance_data_operands.append(SSAValue.get(val))

        instance_name = f"{pe.name_prop.data}_pe_{'_'.join(str(idx) for idx in indexes)}"
        instance = phs.PEInstanceOp(
            instance_name=instance_name,
            pe_ref=pe.name_prop.data,
            data_operands=instance_data_operands,
            switches=switch_args,
            result_types=pe_result_types,
        )
        block.add_op(instance)

        # Update per-chain state with this PE's outputs
        for out_j in reduced_outputs:
            group_key = template_spec.output_maps[out_j].eval(indexes, ())
            chain_state[out_j][group_key] = instance.res[out_j]

        # Collect parallel outputs
        for out_j in parallel_outputs:
            parallel_pe_outputs[out_j].append(instance.res[out_j])

    # Build yield operands
    yield_operands: list[SSAValue] = []
    for j in range(len(pe_result_types)):
        out_size = output_sizes[j]
        if j in parallel_outputs:
            # Fully parallel: assemble from all PE outputs in iteration order
            ops, out_array_val = create_shaped_hw_array(parallel_pe_outputs[j], out_size)
            block.add_ops(ops)
            yield_operands.append(out_array_val)
        elif len(out_size) == 0:
            # Fully reduced: single scalar from the one group with key ()
            yield_operands.append(chain_state[j][()])
        else:
            # Partially reduced: collect last chain values per group in index order
            result_values: list[SSAValue] = []
            for out_idx in itertools.product(*[range(s) for s in out_size]):
                result_values.append(chain_state[j][out_idx])
            ops, out_array_val = create_shaped_hw_array(result_values, out_size)
            block.add_ops(ops)
            yield_operands.append(out_array_val)

    block.add_op(phs.YieldOp(*yield_operands))

    function_type = builtin.FunctionType.from_lists(in_types, out_types)
    return phs.PEArrayOp(
        name=f"{pe.name_prop.data}_array",
        function_type=function_type,
        region=Region(block),
    )


BOUNDS_ATTR_NAME = "phs_array_bounds"


def derive_template_spec(pe: phs.PEOp, bounds: tuple[int, ...]) -> TemplateSpec:
    """Derive a TemplateSpec from a PEOp and array bounds using identity maps."""
    num_data = len(pe.data_operands())
    num_outputs = len(pe.get_terminator().operands)
    num_dims = len(bounds)
    input_maps = tuple(AffineMap.identity(num_dims) for _ in range(num_data))
    output_maps = tuple(AffineMap.identity(num_dims) for _ in range(num_outputs))
    return TemplateSpec(input_maps=input_maps, output_maps=output_maps, template_bounds=bounds)


@dataclass(frozen=True)
class InstantiatePEArrays(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, pe: phs.PEOp, rewriter: PatternRewriter):
        if BOUNDS_ATTR_NAME not in pe.attributes:
            return

        bounds_attr = pe.attributes[BOUNDS_ATTR_NAME]
        if isinstance(bounds_attr, builtin.DenseArrayBase):
            bounds = bounds_attr.get_values()
        elif isinstance(bounds_attr, builtin.DenseIntOrFPElementsAttr):
            bounds = cast(tuple[int, ...], bounds_attr.get_values())
        else:
            raise ValueError(f"Unexpected type for {BOUNDS_ATTR_NAME}: {type(bounds_attr)}")
        template_spec = derive_template_spec(pe, bounds)

        array_op = _build_pe_array_body(pe, template_spec)
        rewriter.insert_op(array_op, InsertPoint.after(pe))

        # Remove the bounds attribute — it's been consumed
        del pe.attributes[BOUNDS_ATTR_NAME]


@dataclass(frozen=True)
class InstantiatePEArrayPass(ModulePass):
    name = "instantiate-pe-array"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        PatternRewriteWalker(InstantiatePEArrays(), apply_recursively=False).rewrite_module(op)

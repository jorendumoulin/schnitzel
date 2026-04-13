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
    - Map produces non-empty shape (e.g. (d0) -> (d0)): input comes from an array,
      indexed per PE iteration. This is a **parallel** input.
    - Map produces empty shape (e.g. (d0) -> ()): input is scalar and does not vary
      across iterations. If a matching scalar output exists, this forms a **chain**:
      the output of PE[i] feeds into the input of PE[i+1], with the first PE getting
      an initial value from a block arg.

    Similarly for outputs:
    - Non-empty shape: outputs are collected into an array.
    - Empty shape: scalar output. If chained, yields the last PE's result.

    This handles data-parallel, reductions, and mixed cases uniformly.
    """
    input_sizes = template_spec.get_input_sizes()
    output_sizes = template_spec.get_output_sizes()

    data_operands = pe.data_operands()
    switches = pe.get_switches()
    yield_op = pe.get_terminator()
    pe_result_types = list(yield_op.operand_types)

    # Determine which inputs are chained (scalar) vs parallel (array)
    # by looking at the shape each input map produces
    chained_inputs: set[int] = set()
    for i, input_size in enumerate(input_sizes):
        if len(input_size) == 0:
            chained_inputs.add(i)

    # Determine which outputs are chained (scalar) vs parallel (array)
    chained_outputs: set[int] = set()
    for j, output_size in enumerate(output_sizes):
        if len(output_size) == 0:
            chained_outputs.add(j)

    # Build input types for the array block args
    in_types: list[Attribute] = []
    parallel_arg_indices: dict[int, int] = {}  # pe_data_idx -> block_arg_idx
    chained_arg_indices: dict[int, int] = {}  # pe_data_idx -> block_arg_idx

    for i, data_opnd in enumerate(data_operands):
        assert isa(data_opnd.type, builtin.AnySignlessIntegerType)
        if i in chained_inputs:
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
        if j in chained_outputs:
            out_types.append(pe_result_types[j])
        else:
            assert isa(yield_op.operands[j].type, builtin.AnySignlessIntegerType)
            out_types.append(cast(Attribute, create_shaped_hw_array_type(yield_op.operands[j].type, output_sizes[j])))

    # Create block
    block = Block(arg_types=in_types)
    switch_args = list(block.args[len(in_types) - len(switches) :])

    pe_outputs_per_result: list[list[SSAValue]] = [[] for _ in range(len(pe_result_types))]
    prev_pe_outputs: list[SSAValue | None] = [None] * len(pe_result_types)

    for indexes in template_spec.get_iterations():
        instance_data_operands: list[SSAValue] = []

        for i in range(len(data_operands)):
            if i in chained_inputs:
                if prev_pe_outputs[0] is None:
                    # First PE: use the initial value block arg
                    instance_data_operands.append(block.args[chained_arg_indices[i]])
                else:
                    # Subsequent PEs: use previous PE's output
                    # Match chained input to the corresponding chained output
                    instance_data_operands.append(prev_pe_outputs[0])
                    # TODO: support multiple chained pairs by matching input/output indices
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

        for j in range(len(pe_result_types)):
            pe_outputs_per_result[j].append(instance.res[j])
            prev_pe_outputs[j] = instance.res[j]

    # Build outputs
    yield_operands: list[SSAValue] = []
    for j in range(len(pe_result_types)):
        if j in chained_outputs:
            # Chained: yield the last PE's output (scalar)
            assert prev_pe_outputs[j] is not None
            yield_operands.append(prev_pe_outputs[j])
        else:
            # Parallel: assemble output array
            ops, out_array_val = create_shaped_hw_array(pe_outputs_per_result[j], output_sizes[j])
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
    fallback_template_spec: TemplateSpec | None

    @op_type_rewrite_pattern
    def match_and_rewrite(self, pe: phs.PEOp, rewriter: PatternRewriter):
        # Read array bounds from PE attribute if present
        if BOUNDS_ATTR_NAME in pe.attributes:
            bounds_attr = pe.attributes[BOUNDS_ATTR_NAME]
            bounds = bounds_attr.get_values()
            template_spec = derive_template_spec(pe, bounds)
        elif self.fallback_template_spec is not None:
            template_spec = self.fallback_template_spec
        else:
            return

        array_op = _build_pe_array_body(pe, template_spec)
        rewriter.insert_op(array_op, InsertPoint.after(pe))

        # Remove the bounds attribute — it's been consumed
        if BOUNDS_ATTR_NAME in pe.attributes:
            del pe.attributes[BOUNDS_ATTR_NAME]


@dataclass(frozen=True)
class InstantiatePEArrayPass(ModulePass):
    name = "instantiate-pe-array"

    template_spec: TemplateSpec | tuple[int, ...] | None = None

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        fallback: TemplateSpec | None = None
        if self.template_spec is not None:
            if not isinstance(self.template_spec, TemplateSpec):
                fixed_input_maps = (
                    AffineMap.from_callable(lambda y: (y,)),
                    AffineMap.from_callable(lambda y: (y,)),
                )
                fixed_output_maps = (AffineMap.from_callable(lambda y: (y,)),)
                fallback = TemplateSpec(
                    input_maps=fixed_input_maps, output_maps=fixed_output_maps, template_bounds=self.template_spec
                )
            else:
                fallback = self.template_spec
        PatternRewriteWalker(
            InstantiatePEArrays(fallback_template_spec=fallback), apply_recursively=False
        ).rewrite_module(op)

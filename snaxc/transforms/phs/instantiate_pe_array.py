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


def _build_pe_array_body(pe: phs.PEOp, template_spec: TemplateSpec) -> phs.PEArrayOp:
    """
    Build a PEArrayOp with explicit wiring in the body:
    - hw.array_get to extract inputs from arrays
    - phs.instance to instantiate PEs
    - hw.array_create to assemble outputs
    - phs.yield to return results
    """
    # Compute array port types
    input_sizes = template_spec.get_input_sizes()
    output_sizes = template_spec.get_output_sizes()

    # Build input types: data ports are shaped arrays, switch ports are scalar index
    in_types: list[Attribute] = []
    data_operands = pe.data_operands()
    switches = pe.get_switches()

    for data_opnd, input_size in zip(data_operands, input_sizes, strict=True):
        assert isa(data_opnd.type, builtin.AnySignlessIntegerType)
        in_types.append(create_shaped_hw_array_type(data_opnd.type, input_size))

    for _switch in switches:
        in_types.append(builtin.IndexType())

    # Build output types: shaped arrays
    yield_op = pe.get_terminator()
    out_types: list[Attribute] = []
    for output, output_size in zip(yield_op.operands, output_sizes, strict=True):
        assert isa(output.type, builtin.AnySignlessIntegerType)
        out_types.append(cast(Attribute, create_shaped_hw_array_type(output.type, output_size)))

    # Create block with input args
    block = Block(arg_types=in_types)

    num_data = len(data_operands)
    data_args = list(block.args[:num_data])
    switch_args = list(block.args[num_data:])

    # Result types for each PE instance (scalar, not arrays)
    pe_result_types = list(yield_op.operand_types)

    # FIXME: Only support single output
    assert len(output_sizes) == 1, "Currently only support single output for array generation"
    pe_outputs: list[SSAValue] = []

    all_maps = template_spec.input_maps + template_spec.output_maps

    for indexes in template_spec.get_iterations():
        instance_data_operands: list[SSAValue] = []

        # Extract data inputs from arrays using affine maps
        for i, data_arg in enumerate(data_args):
            input_indexes = all_maps[i].eval(indexes, ())
            array_val = SSAValue.get(data_arg, type=hw.ArrayType)
            indexing_ops, val = get_from_shaped_hw_array(array_val, input_indexes)
            block.add_ops(indexing_ops)
            instance_data_operands.append(SSAValue.get(val))

        # Create phs.instance
        instance_name = f"{pe.name_prop.data}_pe_{'_'.join(str(idx) for idx in indexes)}"
        instance = phs.PEInstanceOp(
            instance_name=instance_name,
            pe_ref=pe.name_prop.data,
            data_operands=instance_data_operands,
            switches=switch_args,
            result_types=pe_result_types,
        )
        block.add_op(instance)

        assert len(instance.res) == 1
        pe_outputs.append(instance.res[0])

    # Assemble output arrays
    ops, out_array_val = create_shaped_hw_array(pe_outputs, output_sizes[0])
    block.add_ops([*ops, phs.YieldOp(out_array_val)])

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

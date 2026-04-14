"""
PE array instantiation — generates a PEArrayOp body from a TemplateSpec.

The wiring logic is split into three phases so the same building blocks can be
reused for both initial instantiation and array-level merging:

1. **Layout** — derive the block arg structure (which inputs are arrays vs scalar
   chain initial values), and pair chained inputs with reduced outputs.

2. **Resolve** — for each (iteration, input_index), describe where the operand
   should come from (block arg, indexed array element, or another PE's output).
   This is a pure function of the maps + iteration order; it returns a
   `WiringResolution` that has no SSA references.

3. **Materialize** — turn a WiringResolution into actual SSA values, creating
   any needed `hw.array_get` ops.

The merge logic in `combine_arrays.py` reuses Phase 2 to compare the wiring of
two patterns and Phase 3 to materialize new connections behind muxes.
"""

import itertools
from dataclasses import dataclass
from math import prod

from xdsl.dialects import arith, builtin, hw
from xdsl.ir import Attribute, Block, Region, SSAValue
from xdsl.ir.affine import AffineMap
from xdsl.utils.hints import isa

from snaxc.dialects import phs
from snaxc.phs.hw_conversion import (
    create_shaped_hw_array,
    create_shaped_hw_array_type,
    get_from_shaped_hw_array,
)
from snaxc.phs.template_spec import TemplateSpec

# =====================================================================
# Wiring descriptions (pure data, no SSA references)
# =====================================================================


@dataclass(frozen=True)
class FromArrayBlockArg:
    """Read from an array-typed block arg at the given indices."""

    arg_index: int
    indices: tuple[int, ...]


@dataclass(frozen=True)
class FromScalarBlockArg:
    """Read directly from a scalar block arg (initial value of a chain)."""

    arg_index: int


@dataclass(frozen=True)
class FromPEOutput:
    """Read from another PE instance's output (chain link)."""

    iteration: tuple[int, ...]
    output_index: int


WiringResolution = FromArrayBlockArg | FromScalarBlockArg | FromPEOutput


# =====================================================================
# Phase 1: layout — derive block arg structure from a TemplateSpec
# =====================================================================


def _is_scalar_map(m: AffineMap, bounds: tuple[int, ...]) -> bool:
    """True if this map produces a 0-dimensional (scalar) output."""
    return len(m.eval(bounds, ())) == 0


@dataclass(frozen=True)
class ArrayLayout:
    """Describes the block arg structure of a PEArrayOp."""

    in_types: tuple[Attribute, ...]
    out_types: tuple[Attribute, ...]
    # Mapping: PE data input index -> block arg index
    parallel_arg_idx: dict[int, int]
    chained_arg_idx: dict[int, int]
    # Mapping: chained input index -> reduced output index it pairs with
    input_to_output_chain: dict[int, int]
    # Classification (purely derived from spec, kept for convenience)
    chained_inputs: tuple[int, ...]
    reduced_outputs: tuple[int, ...]
    parallel_outputs: tuple[int, ...]


def compute_layout(pe: phs.PEOp, spec: TemplateSpec) -> ArrayLayout:
    """Derive the block arg layout for a PEArrayOp from the spec."""
    bounds = spec.template_bounds
    input_sizes = spec.get_input_sizes()
    output_sizes = spec.get_output_sizes()

    data_operands = pe.data_operands()
    switches = pe.get_switches()
    yield_op = pe.get_terminator()
    pe_result_types = list(yield_op.operand_types)

    chained_inputs = tuple(i for i, m in enumerate(spec.input_maps) if _is_scalar_map(m, bounds))
    reduced_outputs = tuple(j for j, m in enumerate(spec.output_maps) if m.eval(bounds, ()) != bounds)
    parallel_outputs = tuple(j for j in range(len(pe_result_types)) if j not in reduced_outputs)

    input_to_output_chain: dict[int, int] = dict(zip(chained_inputs, reduced_outputs, strict=False))

    in_types: list[Attribute] = []
    parallel_arg_idx: dict[int, int] = {}
    chained_arg_idx: dict[int, int] = {}

    for i, data_opnd in enumerate(data_operands):
        assert isa(data_opnd.type, builtin.AnySignlessIntegerType)
        if i in input_to_output_chain:
            chained_arg_idx[i] = len(in_types)
            in_types.append(data_opnd.type)
        else:
            parallel_arg_idx[i] = len(in_types)
            in_types.append(create_shaped_hw_array_type(data_opnd.type, input_sizes[i]))

    for _ in switches:
        in_types.append(builtin.IndexType())

    # Data outputs come first.
    out_types: list[Attribute] = []
    for j, out_size in enumerate(output_sizes):
        if len(out_size) == 0:
            out_types.append(pe_result_types[j])
        else:
            el_type = yield_op.operands[j].type
            assert isa(el_type, builtin.AnySignlessIntegerType)
            out_types.append(create_shaped_hw_array_type(el_type, out_size))

    # Each output gets a corresponding "valid" mask, appended at the end.
    # Mask width = number of meaningful output positions (1 for scalar, prod(shape) otherwise).
    # The mask drives per-port enable signals on output streamers.
    for out_size in output_sizes:
        out_types.append(builtin.IntegerType(_mask_width_for_size(out_size)))

    return ArrayLayout(
        in_types=tuple(in_types),
        out_types=tuple(out_types),
        parallel_arg_idx=parallel_arg_idx,
        chained_arg_idx=chained_arg_idx,
        input_to_output_chain=input_to_output_chain,
        chained_inputs=chained_inputs,
        reduced_outputs=reduced_outputs,
        parallel_outputs=parallel_outputs,
    )


def _mask_width_for_size(out_size: tuple[int, ...]) -> int:
    """The mask width for an output is the total number of positions it occupies."""
    if len(out_size) == 0:
        return 1
    return prod(out_size)


# =====================================================================
# Phase 2: resolve — describe where each operand should come from
# =====================================================================


def _previous_in_chain(
    current: tuple[int, ...],
    output_map: AffineMap,
    all_iters: list[tuple[int, ...]],
) -> tuple[int, ...] | None:
    """
    Find the previous PE in the same chain group (= same output index).
    Returns None if `current` is the first PE in its group.
    """
    current_group = output_map.eval(current, ())
    current_idx = all_iters.index(current)
    for earlier in reversed(all_iters[:current_idx]):
        if output_map.eval(earlier, ()) == current_group:
            return earlier
    return None


def resolve_input_wiring(
    spec: TemplateSpec,
    layout: ArrayLayout,
    iteration: tuple[int, ...],
    input_index: int,
    all_iters: list[tuple[int, ...]],
) -> WiringResolution:
    """
    Describe where input `input_index` of the PE at `iteration` should come from.
    Pure function — no SSA references, no IR mutation.
    """
    if input_index in layout.input_to_output_chain:
        paired_out = layout.input_to_output_chain[input_index]
        prev = _previous_in_chain(iteration, spec.output_maps[paired_out], all_iters)
        if prev is None:
            # First PE in the chain group → initial value from scalar block arg.
            return FromScalarBlockArg(arg_index=layout.chained_arg_idx[input_index])
        return FromPEOutput(iteration=prev, output_index=paired_out)
    else:
        # Parallel input: read from the array block arg using the input map.
        idx = spec.input_maps[input_index].eval(iteration, ())
        return FromArrayBlockArg(arg_index=layout.parallel_arg_idx[input_index], indices=idx)


def resolve_output_assembly(
    spec: TemplateSpec,
    layout: ArrayLayout,
    output_index: int,
    all_iters: list[tuple[int, ...]],
) -> list[FromPEOutput]:
    """
    Describe which PE outputs feed each position of an output array.
    For parallel outputs, returns one entry per iteration in order.
    For reduced outputs, returns the last PE in each output group.
    """
    out_size = spec.get_output_sizes()[output_index]

    if output_index in layout.parallel_outputs:
        return [FromPEOutput(iteration=it, output_index=output_index) for it in all_iters]

    if len(out_size) == 0:
        # Fully reduced: single scalar = last PE overall.
        return [FromPEOutput(iteration=all_iters[-1], output_index=output_index)]

    # Partially reduced: for each output position, take the last PE in that group.
    output_map = spec.output_maps[output_index]
    positions = list(itertools.product(*[range(s) for s in out_size]))
    result: list[FromPEOutput] = []
    for pos in positions:
        group = [it for it in all_iters if output_map.eval(it, ()) == pos]
        result.append(FromPEOutput(iteration=group[-1], output_index=output_index))
    return result


# =====================================================================
# Phase 3: materialize — turn WiringResolution into SSA values
# =====================================================================


def materialize(
    res: WiringResolution,
    block: Block,
    instances: dict[tuple[int, ...], phs.PEInstanceOp],
) -> SSAValue:
    """Turn a WiringResolution into an SSAValue, building hw.array_get ops if needed."""
    if isinstance(res, FromScalarBlockArg):
        return block.args[res.arg_index]
    if isinstance(res, FromArrayBlockArg):
        array_val = SSAValue.get(block.args[res.arg_index], type=hw.ArrayType)
        get_ops, val = get_from_shaped_hw_array(array_val, res.indices)
        block.add_ops(get_ops)
        return SSAValue.get(val)
    # res must be FromPEOutput
    return instances[res.iteration].res[res.output_index]


# =====================================================================
# Top-level: build a PEArrayOp from a PE + spec using the three phases
# =====================================================================


def build_pe_array_body(pe: phs.PEOp, spec: TemplateSpec) -> phs.PEArrayOp:
    layout = compute_layout(pe, spec)
    block = Block(arg_types=layout.in_types)
    switches = pe.get_switches()
    switch_args = list(block.args[len(layout.in_types) - len(switches) :])

    yield_op = pe.get_terminator()
    pe_result_types = list(yield_op.operand_types)
    all_iters = list(spec.get_iterations())

    # Create all PE instances. We build them one at a time, materializing
    # operands as we go. Chained inputs that depend on later instances aren't
    # an issue because chains always flow forward in iteration order.
    instances: dict[tuple[int, ...], phs.PEInstanceOp] = {}
    for iteration in all_iters:
        operands: list[SSAValue] = []
        for i in range(len(pe.data_operands())):
            res = resolve_input_wiring(spec, layout, iteration, i, all_iters)
            operands.append(materialize(res, block, instances))

        instance = phs.PEInstanceOp(
            instance_name=f"{pe.name_prop.data}_pe_{'_'.join(str(i) for i in iteration)}",
            pe_ref=pe.name_prop.data,
            data_operands=operands,
            switches=switch_args,
            result_types=pe_result_types,
        )
        block.add_op(instance)
        instances[iteration] = instance

    # Assemble data outputs from per-output PE references.
    yield_operands: list[SSAValue] = []
    output_sizes = spec.get_output_sizes()
    for j in range(len(pe_result_types)):
        sources = resolve_output_assembly(spec, layout, j, all_iters)
        materialized = [materialize(s, block, instances) for s in sources]
        out_size = output_sizes[j]
        if len(out_size) == 0:
            # Scalar
            yield_operands.append(materialized[0])
        else:
            ops, array_val = create_shaped_hw_array(materialized, out_size)
            block.add_ops(ops)
            yield_operands.append(array_val)

    # Append a per-output "valid" mask. For a fresh array (no merges yet), every
    # output position is meaningful, so the mask is all-ones.
    for out_size in output_sizes:
        width = _mask_width_for_size(out_size)
        all_ones = (1 << width) - 1
        const = arith.ConstantOp.from_int_and_width(all_ones, width)
        block.add_op(const)
        yield_operands.append(const.result)

    block.add_op(phs.YieldOp(*yield_operands))

    function_type = builtin.FunctionType.from_lists(layout.in_types, layout.out_types)
    return phs.PEArrayOp(
        name=f"{pe.name_prop.data}_array",
        function_type=function_type,
        region=Region(block),
    )

"""
Merge two PE array wiring patterns into one PEArrayOp.

Given an existing PEArrayOp (the "abstract" array) and a new TemplateSpec
describing additional wiring, this module modifies the abstract array
in-place to support both patterns. Where the wiring differs, a phs.MuxOp
is inserted, controlled by a new array-level switch.

This reuses the wiring primitives from instantiate_pe_array:
- Phase 2 (resolve) turns "spec + iteration + input" into a WiringResolution
- Phase 3 (materialize) turns a WiringResolution into an SSA value

For the merge, we additionally need an "inverse" — given an existing SSA
operand, figure out which WiringResolution it corresponds to. Then we can
compare current vs proposed resolutions structurally and only insert a mux
where they truly differ.
"""

from xdsl.dialects import arith, hw
from xdsl.ir import Block, BlockArgument, SSAValue

from snaxc.dialects import phs
from snaxc.phs.hw_conversion import trace_hw_array_get_chain
from snaxc.phs.instantiate_array import (
    FromArrayBlockArg,
    FromPEOutput,
    FromScalarBlockArg,
    WiringResolution,
    compute_layout,
    resolve_input_wiring,
)
from snaxc.phs.template_spec import TemplateSpec


def _classify_existing_operand(
    operand: SSAValue,
    instances: list[phs.PEInstanceOp],
    iterations: list[tuple[int, ...]],
) -> WiringResolution:
    """
    Inverse of `materialize`: given an SSA operand inside a PEArrayOp body,
    figure out what WiringResolution it corresponds to.

    Handles the three cases:
    - Direct block arg → FromScalarBlockArg
    - Chain of hw.array_get on a block arg → FromArrayBlockArg
    - Result of a PEInstanceOp → FromPEOutput (mapping the instance back to its iteration)
    """
    # Build instance -> iteration lookup
    instance_to_iter = {inst: it for inst, it in zip(instances, iterations, strict=True)}

    # Case 1: direct block arg
    if isinstance(operand, BlockArgument):
        return FromScalarBlockArg(arg_index=operand.index)

    owner = operand.owner

    # Case 2: PE instance output
    if isinstance(owner, phs.PEInstanceOp):
        for j, res in enumerate(owner.res):
            if res is operand:
                return FromPEOutput(iteration=instance_to_iter[owner], output_index=j)
        raise AssertionError("operand not found among instance results")

    # Case 3: hw.array_get chain → trace back to block arg, collecting indices
    if isinstance(owner, hw.ArrayGetOp):
        root, indices = trace_hw_array_get_chain(operand)
        assert isinstance(root, BlockArgument), f"hw.array_get chain doesn't terminate at a block arg, got {root}"
        return FromArrayBlockArg(arg_index=root.index, indices=indices)

    raise NotImplementedError(f"Cannot classify operand: {operand} (owner: {owner})")


def merge_pe_array_wiring(
    abstract_array: phs.PEArrayOp,
    new_spec: TemplateSpec,
    pe: phs.PEOp,
) -> None:
    """
    Merge a new wiring pattern into an existing PEArrayOp.

    For each PE instance, compare the current operand wiring (from IR) with
    what the new spec would produce. Where they differ, insert a mux controlled
    by a new array-level switch.

    Requires both wirings to share the same block arg structure (same number
    and types of array inputs). Differences in port structure (e.g., a scalar
    initial-value port vs an array input port) cannot be merged — those need
    separate accelerators.

    The abstract array is modified in-place.
    """
    instances = abstract_array.get_instances()
    block = abstract_array.body.block

    iterations = list(new_spec.get_iterations())
    assert len(iterations) == len(instances), (
        f"Iteration count ({len(iterations)}) doesn't match instance count ({len(instances)})"
    )

    # Compute layout for the new spec.
    new_layout = compute_layout(pe, new_spec)

    # Compatibility check: the new layout's block arg types (excluding switches)
    # must match the existing array's (excluding any array-level switches).
    existing_arg_types = list(block.args)
    n_array_sw = abstract_array.array_switch_no.value.data
    # Trim array switches off the existing args to compare data + PE switches only
    existing_data_arg_types = [a.type for a in existing_arg_types[: len(existing_arg_types) - n_array_sw]]
    new_data_arg_types = list(new_layout.in_types)
    assert existing_data_arg_types == new_data_arg_types, (
        f"Cannot merge: block arg types differ.\n"
        f"  existing: {existing_data_arg_types}\n"
        f"  new spec: {new_data_arg_types}"
    )

    instances_by_iter: dict[tuple[int, ...], phs.PEInstanceOp] = dict(zip(iterations, instances, strict=True))

    array_switch: BlockArgument | None = None
    num_data = len(pe.data_operands())

    for iteration, instance in zip(iterations, instances, strict=True):
        for i in range(num_data):
            proposed = resolve_input_wiring(new_spec, new_layout, iteration, i, iterations)
            current_operand = instance.data_operands[i]
            current = _classify_existing_operand(current_operand, instances, iterations)

            if current == proposed:
                continue  # already wired the way the new spec wants

            if array_switch is None:
                array_switch = abstract_array.add_array_switch()

            # Materialize the proposed resolution, inserting any new ops
            # just before this PE instance.
            proposed_val = _materialize_before(proposed, block, instances_by_iter, instance)

            mux = phs.MuxOp(
                lhs=current_operand,
                rhs=proposed_val,
                switch=array_switch,
            )
            block.insert_op_before(mux, instance)
            instance.operands[i] = mux.res


def _materialize_before(
    res: WiringResolution,
    block: Block,
    instances: dict[tuple[int, ...], phs.PEInstanceOp],
    before_op: phs.PEInstanceOp,
) -> SSAValue:
    """
    Like `materialize`, but inserts new ops just before `before_op` instead
    of appending to the block.
    """
    if isinstance(res, FromScalarBlockArg):
        return block.args[res.arg_index]
    if isinstance(res, FromArrayBlockArg):
        # Build hw.array_get chain manually so we can position the ops.
        current = block.args[res.arg_index]
        for idx in res.indices:
            assert isinstance(current.type, hw.ArrayType)
            bitwidth = (current.type.size_attr.data - 1).bit_length()
            const = arith.ConstantOp.from_int_and_width(idx, max(bitwidth, 1))
            get = hw.ArrayGetOp(current, const)
            block.insert_op_before(const, before_op)
            block.insert_op_before(get, before_op)
            current = get.result
        return current
    # FromPEOutput
    return instances[res.iteration].res[res.output_index]

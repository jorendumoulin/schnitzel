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

from xdsl.dialects import arith, builtin, hw
from xdsl.ir import Attribute, Block, BlockArgument, Region, SSAValue
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
    # Mapping: chained input index -> reduced output index it pairs with.
    # Used for SPATIAL-chain wiring only (FromScalarBlockArg / FromPEOutput).
    input_to_output_chain: dict[int, int]
    # Mapping: PE input index -> PE output index that share a logical streamer.
    # Used for streamer/mask accounting (read+write coalesce into readWrite).
    # Superset of input_to_output_chain — also includes positional readWrite
    # pairs from the encode-pass convention (last K inputs paired with K outputs).
    streamer_pairs: dict[int, int]
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

    reduced_outputs = tuple(j for j, m in enumerate(spec.output_maps) if m.eval(bounds, ()) != bounds)
    parallel_outputs = tuple(j for j in range(len(pe_result_types)) if j not in reduced_outputs)

    # Spatial chain pairs. A paired carry whose paired output is reduced (the
    # output map drops at least one bounds dim) becomes a spatial chain along
    # the dropped dim(s). Each PE in the same output-group reads its carry
    # from the previous PE in iteration order; the first PE in the group
    # reads the carry init from the block arg. This subsumes the fully-reduced
    # case (output map → ()) where the chain init is a scalar; for partial
    # reduction (output map keeps some bounds dims) the carry init is an
    # array indexed by the group's output position.
    input_to_output_chain: dict[int, int] = {
        in_idx: out_idx for in_idx, out_idx in spec.readwrite_pairs.items() if out_idx in reduced_outputs
    }
    chained_inputs = tuple(sorted(input_to_output_chain))
    # Streamer-level pairs: union with positional readWrite pairs from the spec
    # (encode-pass convention). Drives streamer/mask accounting only — temporal
    # readWrite inputs are still wired as parallel array reads, not chains.
    streamer_pairs: dict[int, int] = {**input_to_output_chain, **spec.readwrite_pairs}

    in_types: list[Attribute] = []
    parallel_arg_idx: dict[int, int] = {}
    chained_arg_idx: dict[int, int] = {}

    for i, data_opnd in enumerate(data_operands):
        assert isa(data_opnd.type, builtin.AnySignlessIntegerType)
        if i in input_to_output_chain:
            # Carry init port: shape follows the carry input's own access map
            # (= the paired output's map). For a fully-reduced chain this is
            # the scalar element type; for partial reduction it is an
            # hw.array of the output's shape.
            chained_arg_idx[i] = len(in_types)
            in_types.append(create_shaped_hw_array_type(data_opnd.type, input_sizes[i]))
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

    # One per-spatial-dim enable mask per *logical streamer*. A streamer is:
    #   - a pure read:      one PE input that is NOT chained to an output
    #   - a readWrite:      a PE input that IS chained to an output (counted once)
    #   - a pure write:     one PE output that is NOT a chain target
    # Ordering: iterate PE inputs in order first (emitting read or readWrite masks),
    # then iterate PE outputs in order skipping ones already counted as chain targets
    # (emitting write masks). This ordering matches `config.streamers` on the Chisel
    # side and the `mask_{streamerIdx}` port naming.
    paired_output_set = set(streamer_pairs.values())
    for i in range(len(data_operands)):
        if i in streamer_pairs:
            # readWrite streamer: spatial dims come from the paired output.
            paired_j = streamer_pairs[i]
            out_types.append(builtin.IntegerType(_mask_width_for_size(output_sizes[paired_j])))
        else:
            out_types.append(builtin.IntegerType(_mask_width_for_size(input_sizes[i])))
    for j in range(len(pe_result_types)):
        if j in paired_output_set:
            continue  # already counted as the readWrite partner of some input
        out_types.append(builtin.IntegerType(_mask_width_for_size(output_sizes[j])))

    # One `carry_used_K` i1 output per readWrite pair. Scala uses these to
    # gate `writeData.valid` at runtime so merged PEs whose carry is used in
    # some modes but not others don't deadlock in the "no carry needed" modes.
    for _ in streamer_pairs:
        out_types.append(builtin.IntegerType(1))

    return ArrayLayout(
        in_types=tuple(in_types),
        out_types=tuple(out_types),
        parallel_arg_idx=parallel_arg_idx,
        chained_arg_idx=chained_arg_idx,
        input_to_output_chain=input_to_output_chain,
        streamer_pairs=streamer_pairs,
        chained_inputs=chained_inputs,
        reduced_outputs=reduced_outputs,
        parallel_outputs=parallel_outputs,
    )


def _mask_width_for_size(out_size: tuple[int, ...]) -> int:
    """
    Mask width is the number of spatial dimensions — one enable bit per dim.
    A zero-dim (scalar) output still gets a single bit so the IR has a valid
    ``IntegerType`` (bitwidth >= 1); its semantic is "always on."
    """
    return max(1, len(out_size))


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
        output_map = spec.output_maps[paired_out]
        prev = _previous_in_chain(iteration, output_map, all_iters)
        if prev is None:
            # First PE in the chain group → read the carry init from the
            # block arg. For a fully-reduced output the block arg is a
            # scalar; for partial reduction it is an array indexed by this
            # group's position in output space.
            group_pos = output_map.eval(iteration, ())
            if group_pos == ():
                return FromScalarBlockArg(arg_index=layout.chained_arg_idx[input_index])
            return FromArrayBlockArg(arg_index=layout.chained_arg_idx[input_index], indices=group_pos)
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
# Dynamic carry-used expression
# =====================================================================
#
# For each readWrite streamer, the Scala accelerator wants to know at runtime
# whether the BlackBox's output actually depends on that streamer's carry-input
# this cycle. It's a boolean function of the PE's switches. We build it by
# walking the PE body backwards from the yielded value for the paired output,
# tracking "does this value depend on the carry block-arg under the current
# switch values?" and materializing the resulting i1 expression in the array
# body using array-level switches.


def _compute_carry_used_expr(
    val: SSAValue,
    carry_arg: BlockArgument,
    pe_sw_to_array_sw: dict[SSAValue, SSAValue],
    array_block: Block,
    subst: dict[SSAValue, SSAValue],
    cache: dict[SSAValue, SSAValue],
) -> SSAValue:
    """Build an i1 SSA value (inserted into ``array_block``) that evaluates true
    when ``val`` (a PE-body value) transitively depends on ``carry_arg`` (a PE
    block arg) given the current runtime switch values."""

    # Apply block-arg substitution (used when recursing into a choose case:
    # the case's block args map positionally to the ChooseOp's data_operands).
    if val in subst:
        val = subst[val]

    if val in cache:
        return cache[val]

    def _const_i1(v: int) -> SSAValue:
        op = arith.ConstantOp.from_int_and_width(v, 1)
        array_block.add_op(op)
        return op.result

    def _or(vals: list[SSAValue]) -> SSAValue:
        if not vals:
            return _const_i1(0)
        acc = vals[0]
        for v2 in vals[1:]:
            op = arith.OrIOp(acc, v2)
            array_block.add_op(op)
            acc = op.result
        return acc

    def _and(a: SSAValue, b: SSAValue) -> SSAValue:
        op = arith.AndIOp(a, b)
        array_block.add_op(op)
        return op.result

    def _not(a: SSAValue) -> SSAValue:
        one = _const_i1(1)
        op = arith.XOrIOp(a, one)
        array_block.add_op(op)
        return op.result

    def _switch_as_i1(pe_switch: SSAValue) -> SSAValue:
        """Produce an i1 that is 1 when the switch evaluates to 1 (i.e. the
        mux selects its RHS). For now we only support 1-bit switches (muxes);
        wider switches driving multi-case phs.choose would need per-case
        comparisons and aren't reachable via this helper yet.

        At PEArrayOp-build time the switch block arg is IndexType. After
        convert-pe-to-hw it becomes IntegerType(bitwidth) with an
        UnrealizedConversionCastOp back to IndexType for existing uses. We
        emit the inverse cast here (IndexType → IntegerType(1)); the chain
        IntegerType(1) → IndexType → IntegerType(1) collapses via
        reconcile_unrealized_casts so nothing survives the lowering.
        """
        arr_sw = pe_sw_to_array_sw[pe_switch]
        cast_op, cast_res = builtin.UnrealizedConversionCastOp.cast_one(arr_sw, builtin.IntegerType(1))
        array_block.add_op(cast_op)
        return cast_res

    if isinstance(val, BlockArgument):
        result = _const_i1(1 if val is carry_arg else 0)
    else:
        owner = val.owner
        if isinstance(owner, phs.MuxOp):
            lhs_uses = _compute_carry_used_expr(owner.lhs, carry_arg, pe_sw_to_array_sw, array_block, subst, cache)
            rhs_uses = _compute_carry_used_expr(owner.rhs, carry_arg, pe_sw_to_array_sw, array_block, subst, cache)
            sw = _switch_as_i1(owner.switch)
            not_sw = _not(sw)
            result = _or([_and(not_sw, lhs_uses), _and(sw, rhs_uses)])
        elif isinstance(owner, phs.ChooseOp):
            choose_op = owner
            regions = list(choose_op.regions)
            # For each case, recurse with block-arg substitution so the case's
            # body uses are expressed in terms of the ChooseOp's data_operands
            # (accessible in the enclosing scope).
            case_uses: list[SSAValue] = []
            for case_region in regions:
                case = case_region.block
                case_yield = case.ops.last
                assert isinstance(case_yield, phs.YieldOp)
                new_subst = dict(subst)
                for k, barg in enumerate(case.args):
                    new_subst[barg] = choose_op.data_operands[k]
                case_uses.append(
                    _compute_carry_used_expr(
                        case_yield.operands[0], carry_arg, pe_sw_to_array_sw, array_block, new_subst, cache
                    )
                )
            if len(case_uses) == 1:
                # Single-case choose: result = the one case's expression; no
                # switch gating needed (and the switch may even be dead).
                result = case_uses[0]
            else:
                # Multi-case: carry_used(choose.res) =
                #   OR_i  (switch == i) AND case_uses[i]
                # We only support switches that the _switch_as_i1 helper can
                # project to an i1 (i.e. 1-bit mux-style switches). For a
                # 2-case ChooseOp with a 1-bit switch, case 0 selects when
                # the switch is 0, case 1 when it's 1. Map each case-index
                # directly to a switch-value test.
                if len(case_uses) > 2:
                    raise NotImplementedError(
                        f"phs.choose with {len(case_uses)} cases — need log2-bit comparisons "
                        "for carry-used expression; only 1-bit switches supported today."
                    )
                sw = _switch_as_i1(choose_op.switch)
                not_sw = _not(sw)
                result = _or([_and(not_sw, case_uses[0]), _and(sw, case_uses[1])])
        else:
            # Generic op — result depends on the OR of its operands' carry-usage.
            operand_exprs = [
                _compute_carry_used_expr(o, carry_arg, pe_sw_to_array_sw, array_block, subst, cache)
                for o in owner.operands
            ]
            result = _or(operand_exprs)

    cache[val] = result
    return result


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

    # Append per-spatial-dim enable masks, one per logical streamer. Ordering
    # matches compute_layout: PE inputs first (read or readWrite), then
    # outputs that aren't paired with an input. Each mask bit d is set iff
    # SOME mode's access map for this streamer references dim d — i.e., the
    # OR across modes of "uses dim d." Modes that don't use a streamer (dead
    # slot after widening) contribute nothing. A streamer scalar in every
    # mode collapses to mask=0 (only lane 0 fires); a streamer vectorised in
    # any mode gets the corresponding bits set. This is a safe superset:
    # modes that want fewer lanes still get correct data (stride=0 replicates
    # the scalar to unused lanes at the stream-config level).
    input_sizes = spec.get_input_sizes()
    streamer_mask_sizes: list[tuple[int, ...]] = []
    streamer_mask_maps: list[tuple[AffineMap | None, ...]] = []

    def _output_maps_for(j: int) -> tuple[AffineMap | None, ...]:
        return tuple(mode_maps[j] if j < len(mode_maps) else None for mode_maps in spec.per_mode_output_maps)

    def _input_maps_for(i: int) -> tuple[AffineMap | None, ...]:
        return tuple(mode_maps[i] if i < len(mode_maps) else None for mode_maps in spec.per_mode_input_maps)

    for i in range(len(pe.data_operands())):
        if i in layout.streamer_pairs:
            paired_j = layout.streamer_pairs[i]
            streamer_mask_sizes.append(output_sizes[paired_j])
            # readWrite streamer: its spatial access is the paired output's map.
            streamer_mask_maps.append(_output_maps_for(paired_j))
        else:
            streamer_mask_sizes.append(input_sizes[i])
            streamer_mask_maps.append(_input_maps_for(i))
    paired_output_set = set(layout.streamer_pairs.values())
    for j in range(len(pe_result_types)):
        if j in paired_output_set:
            continue
        streamer_mask_sizes.append(output_sizes[j])
        streamer_mask_maps.append(_output_maps_for(j))

    num_dims = len(spec.template_bounds)
    for size, mode_maps in zip(streamer_mask_sizes, streamer_mask_maps, strict=True):
        width = _mask_width_for_size(size)
        # Union across modes of which of *this streamer's own* spatial dims are
        # active. Bit r corresponds to the r-th result of the affine map (=
        # the r-th spatial dim of the streamer's data), NOT to iteration-space
        # dim r. A streamer-dim is "active" in a mode if its corresponding
        # result expression depends on at least one iteration dim (a constant
        # result means the streamer never advances along that dim → scalar).
        # If a mode's map has a different dim count from the template bounds,
        # its dim-numbering doesn't correspond to PE-array dims and the dart
        # scheduler handles the tile split elsewhere — treat as "all active"
        # (conservative). A mode that's dead (None) contributes nothing.
        used_bits = 0
        for m in mode_maps:
            if m is None:
                continue
            if m.num_dims != num_dims:
                used_bits |= (1 << width) - 1
                continue
            for r_idx, result in enumerate(m.results):
                if r_idx >= width:
                    break
                if result.used_dims():
                    used_bits |= 1 << r_idx
        # Scalar streamers have width=1 by convention (Integer port must be
        # >=1 bit); a scalar-in-every-mode streamer ends up with used_bits=0
        # and we emit the scalar-collapse mask.
        mask_val = used_bits & ((1 << width) - 1)
        const = arith.ConstantOp.from_int_and_width(mask_val, width)
        block.add_op(const)
        yield_operands.append(const.result)

    # Build per-pair dynamic carry_used i1 signals. For each pair (input i,
    # output j) we trace the PE body from the yielded value for output j and
    # ask "does this value depend on the carry block-arg at PE-input position
    # i under the current switch values?" The resulting i1 expression uses
    # array-level switches (mapped from PE switches via `pe_sw_to_array_sw`).
    num_data = len(pe.data_operands())
    pe_switches = pe.get_switches()
    pe_sw_to_array_sw: dict[SSAValue, SSAValue] = {
        pe_sw: block.args[num_data + idx] for idx, pe_sw in enumerate(pe_switches)
    }
    pe_yield = pe.get_terminator()
    cache: dict[SSAValue, SSAValue] = {}
    for in_idx, out_idx in sorted(layout.streamer_pairs.items()):
        carry_arg = pe.body.block.args[in_idx]
        assert isinstance(carry_arg, BlockArgument)
        yielded_val = pe_yield.operands[out_idx]
        carry_used_val = _compute_carry_used_expr(
            yielded_val, carry_arg, pe_sw_to_array_sw, block, subst={}, cache=cache
        )
        yield_operands.append(carry_used_val)

    block.add_op(phs.YieldOp(*yield_operands))

    function_type = builtin.FunctionType.from_lists(layout.in_types, layout.out_types)
    array_op = phs.PEArrayOp(
        name=f"{pe.name_prop.data}_array",
        function_type=function_type,
        region=Region(block),
    )
    # Record the number of readWrite pairs so downstream (convert-pe-array-to-hw)
    # can name the trailing carry_used yields correctly without re-walking the
    # referenced PE.
    array_op.attributes["phs.readwrite_count"] = builtin.IntegerAttr(len(layout.streamer_pairs), 64)
    return array_op

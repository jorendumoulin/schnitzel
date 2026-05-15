"""
Sink `round_raw_to_rec_fn` past `hw.array_get` so a single rounder can be
shared across all branches of a mutex.

After `FinalizePhsToHWPass` inlines `phs.choose` regions, a slot that was
yielding a rounded value in each region appears as:

    %r0 = hardfloat.round_raw_to_rec_fn(%inv0, %raw0, %rm, %tn) : ...
    %r1 = hardfloat.round_raw_to_rec_fn(%inv1, %raw1, %rm, %tn) : ...
    %arr = hw.array_create %r0, %r1 : i33
    %out = hw.array_get %arr[%switch] : !hw.array<2xi33>

The rounders consume different SSA values so plain CSE can't merge them.
This pass rewrites the pattern to mux the raw-bus inputs and run one
rounder after the mux:

    %inv_arr = hw.array_create %inv0, %inv1 : i1
    %raw_arr = hw.array_create %raw0, %raw1 : i41
    %inv = hw.array_get %inv_arr[%switch] : !hw.array<2xi1>
    %raw = hw.array_get %raw_arr[%switch] : !hw.array<2xi41>
    %out = hardfloat.round_raw_to_rec_fn(%inv, %raw, %rm, %tn) : ...

CSE later removes the original `array_create` if its result has no other
users.

Conditions for the rewrite to fire on a given `hw.array_get`:

* The array source is a `hw.array_create` whose every operand is defined
  by a `hardfloat.round_raw_to_rec_fn`.
* All rounders share the same `roundingMode` and `detectTininess` operand
  SSA values, and the same `sig_width`/`exp_width` properties.

Both conditions are met by the typical hardware-pipeline flow where every
region rounds with the same hard-wired rounding mode + tininess constants.
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import hw
from xdsl.dialects.builtin import IntegerType, ModuleOp
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from snaxc.dialects.hardfloat import RoundRawToRecFnOp


class SinkRounderPastArrayGet(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: hw.ArrayGetOp, rewriter: PatternRewriter):
        # Source must be an array_create.
        array_create = op.input.owner
        if not isinstance(array_create, hw.ArrayCreateOp):
            return

        # Bucket rounder lanes by (sig, exp, rm_SSA, tininess_SSA). Each
        # bucket whose population is >=2 collapses into one shared rounder.
        # Non-rounder lanes and singleton rounders pass through unchanged.
        groups: dict[tuple, list[tuple[int, RoundRawToRecFnOp]]] = {}
        for idx, inp in enumerate(array_create.inputs):
            d = inp.owner
            if isinstance(d, RoundRawToRecFnOp):
                key = (d.sig_width.data, d.exp_width.data, id(d.roundingMode), id(d.detectTininess))
                groups.setdefault(key, []).append((idx, d))

        sharable = {k: v for k, v in groups.items() if len(v) >= 2}
        if not sharable:
            return

        n = len(array_create.inputs)
        new_ops: list = []
        # Start with the original lane values; we'll overwrite the lanes
        # that get folded into a shared rounder.
        result_inputs = list(array_create.inputs)
        erased_rounders: list[RoundRawToRecFnOp] = []

        for members in sharable.values():
            head = members[0][1]
            member_by_idx = {idx: r for idx, r in members}
            # At lanes inside this group, feed their own (inv, raw). At
            # other lanes, feed the head member's (inv, raw) as don't-care
            # — the shared rounder still runs but its output is discarded
            # by the result-array at those lanes.
            inv_inputs = [
                member_by_idx[i].invalidExc if i in member_by_idx else head.invalidExc for i in range(n)
            ]
            raw_inputs = [
                member_by_idx[i].in_ if i in member_by_idx else head.in_ for i in range(n)
            ]
            inv_arr = hw.ArrayCreateOp(*inv_inputs)
            raw_arr = hw.ArrayCreateOp(*raw_inputs)
            inv_get = hw.ArrayGetOp(inv_arr.result, op.index)
            raw_get = hw.ArrayGetOp(raw_arr.result, op.index)
            shared = RoundRawToRecFnOp(
                [inv_get.result, raw_get.result, head.roundingMode, head.detectTininess],
                [head.out.type, IntegerType(5)],
                head.sig_width.data,
                head.exp_width.data,
            )
            new_ops.extend([inv_arr, raw_arr, inv_get, raw_get, shared])
            for idx, r in members:
                result_inputs[idx] = shared.out
                erased_rounders.append(r)

        # If after folding every lane carries the same SSA value, skip the
        # result-array rebuild and substitute that value directly.
        if all(v is result_inputs[0] for v in result_inputs):
            rewriter.replace_op(op, new_ops=new_ops, new_results=[result_inputs[0]])
        else:
            result_arr = hw.ArrayCreateOp(*result_inputs)
            new_get = hw.ArrayGetOp(result_arr.result, op.index)
            new_ops.extend([result_arr, new_get])
            rewriter.replace_op(op, new_ops=new_ops, new_results=[new_get.result])

        # Cleanup: original array_create has no users now. Erase it, then
        # erase the merged rounders that no longer have any uses. Skip
        # rounders that still feed something else.
        if not array_create.result.uses:
            rewriter.erase_op(array_create)
            for r in erased_rounders:
                if not r.out.uses and not r.exceptionFlags.uses:
                    rewriter.erase_op(r)


class SinkRounderPastArrayGetPass(ModulePass):
    """
    Move `round_raw_to_rec_fn` past `hw.array_get` so a single rounder is
    shared across a mutex set of raw-bus producers.
    """

    name = "sink-rounder-past-array-get"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        PatternRewriteWalker(
            SinkRounderPastArrayGet(),
            apply_recursively=False,
        ).rewrite_module(op)

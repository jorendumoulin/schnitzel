"""
Merge / share hardfloat ops across mutex regions visible as
`hw.array_get(hw.array_create(...))`.

Two rewrite patterns share the same access shape:

1. **Sink a rounder past the array_get.** Bucket lanes whose value is
   produced by `round_raw_to_rec_fn` by their `(sig, exp, rm_SSA,
   tininess_SSA)` fingerprint; each bucket of two or more lanes
   collapses into one shared rounder fed by per-bus muxes for
   `invalidExc` and the raw input. Lanes outside any sharable bucket
   keep their original value through a rebuilt result-array.

2. **Share a non-rounder hardfloat op with one or more muxable
   operands.** Driven by `_MUXABLE_OPS`: a per-op-class table listing
   operand indices that may legally differ across lanes (everything
   else must match by SSA identity). Lanes in a group collapse into
   one shared op whose muxable operands are array_get'd through the
   same switch.

Both patterns run post-`FinalizePhsToHWPass` and need no `phs` knowledge.
Both bail out safely when any per-lane op has results other than the
one feeding the array_create with downstream uses (so we don't silently
lose `exceptionFlags` users).
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.context import Context
from xdsl.dialects import hw
from xdsl.dialects.builtin import IntegerType, ModuleOp
from xdsl.ir import Operation, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from snaxc.dialects.hardfloat import (
    AddRawFnOp,
    AddRecFnOp,
    HardfloatOperation,
    InToRecFnOp,
    RecFnToInOp,
    RoundRawToRecFnOp,
)

# (op_class, muxable_operand_indices). Operands at the listed indices may
# differ across lanes; everything else must match by SSA identity.
_MUXABLE_OPS: dict[type[HardfloatOperation], tuple[int, ...]] = {
    AddRecFnOp: (0,),  # subOp distinguishes addf from subf
    AddRawFnOp: (0,),  # same role post-split
    InToRecFnOp: (0,),  # signedIn distinguishes sitofp from uitofp
    RecFnToInOp: (2,),  # signedOut distinguishes fptosi from fptoui
}


def _structural_key(op: HardfloatOperation, mux_idxs: tuple[int, ...]) -> tuple[object, ...]:
    """SSA-identity tuple of non-muxable operands + widths. Two ops with
    the same key are eligible to be folded into one shared op."""
    keep: list[object] = [id(o) for i, o in enumerate(op.operands) if i not in mux_idxs]
    keep.append(op.sig_width.data)
    keep.append(op.exp_width.data)
    if op.int_width is not None:
        keep.append(op.int_width.data)
    return tuple(keep)


class SinkRounder(RewritePattern):
    """Lift a shared `round_raw_to_rec_fn` out from behind an array_get."""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: hw.ArrayGetOp, rewriter: PatternRewriter):
        array_create = op.input.owner
        if not isinstance(array_create, hw.ArrayCreateOp):
            return

        # Bucket rounder lanes by (sig, exp, rm_SSA, tn_SSA).
        groups: dict[tuple[object, ...], list[tuple[int, RoundRawToRecFnOp]]] = {}
        for idx, inp in enumerate(array_create.inputs):
            d = inp.owner
            if isinstance(d, RoundRawToRecFnOp):
                key: tuple[object, ...] = (
                    d.sig_width.data,
                    d.exp_width.data,
                    id(d.roundingMode),
                    id(d.detectTininess),
                )
                groups.setdefault(key, []).append((idx, d))

        sharable = {k: v for k, v in groups.items() if len(v) >= 2}
        if not sharable:
            return

        n = len(array_create.inputs)
        new_ops: list[Operation] = []
        result_inputs: list[SSAValue] = list(array_create.inputs)
        erased: list[HardfloatOperation] = []

        for members in sharable.values():
            head = members[0][1]
            by_idx = {idx: r for idx, r in members}
            # Lanes inside this bucket feed their own (inv, raw); other
            # lanes get the head's values as don't-care fills (result is
            # discarded by the rebuilt result-array anyway).
            inv_inputs = [by_idx[i].invalidExc if i in by_idx else head.invalidExc for i in range(n)]
            raw_inputs = [by_idx[i].in_ if i in by_idx else head.in_ for i in range(n)]
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
                erased.append(r)

        _finalize_replace(op, array_create, new_ops, result_inputs, erased, rewriter)


class ShareMuxableOp(RewritePattern):
    """Collapse lanes of a muxable op class into one shared instance."""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: hw.ArrayGetOp, rewriter: PatternRewriter):
        array_create = op.input.owner
        if not isinstance(array_create, hw.ArrayCreateOp):
            return

        # Bucket lanes by (op_class, structural_key). Skip lanes whose
        # defining op isn't a registered muxable kind, or whose other
        # results are observed downstream.
        groups: dict[
            tuple[type[HardfloatOperation], tuple[object, ...]],
            list[tuple[int, HardfloatOperation, int]],
        ] = {}
        for idx, inp in enumerate(array_create.inputs):
            d = inp.owner
            if not isinstance(d, HardfloatOperation):
                continue
            cls: type[HardfloatOperation] = type(d)
            if cls not in _MUXABLE_OPS:
                continue
            mux_idxs = _MUXABLE_OPS[cls]
            # Locate which of d's results this lane took.
            this_idx = next((i for i, r in enumerate(d.results) if r is inp), None)
            if this_idx is None:
                continue
            # If any *other* result is used, we'd silently drop those users.
            if any(r.uses for i, r in enumerate(d.results) if i != this_idx):
                continue
            key = (cls, _structural_key(d, mux_idxs))
            groups.setdefault(key, []).append((idx, d, this_idx))

        sharable = {k: v for k, v in groups.items() if len(v) >= 2}
        if not sharable:
            return

        n = len(array_create.inputs)
        new_ops: list[Operation] = []
        result_inputs: list[SSAValue] = list(array_create.inputs)
        erased: list[HardfloatOperation] = []

        for (cls, _), members in sharable.items():
            mux_idxs = _MUXABLE_OPS[cls]
            head = members[0][1]
            by_idx: dict[int, HardfloatOperation] = {idx: r for idx, r, _ in members}
            # Build a muxed value per muxable operand index, defaulting
            # non-member lanes to the head's value (don't-care fill).
            muxed_operands: list[SSAValue] = list(head.operands)
            for mi in mux_idxs:
                fills: list[SSAValue] = [by_idx[i].operands[mi] if i in by_idx else head.operands[mi] for i in range(n)]
                arr = hw.ArrayCreateOp(*fills)
                get = hw.ArrayGetOp(arr.result, op.index)
                new_ops.extend([arr, get])
                muxed_operands[mi] = get.result

            int_width_arg = head.int_width.data if head.int_width is not None else None
            shared = cls(
                operands=muxed_operands,
                result_types=[r.type for r in head.results],
                sig_width=head.sig_width.data,
                exp_width=head.exp_width.data,
                int_width=int_width_arg,
            )
            new_ops.append(shared)

            for idx, r, res_idx in members:
                result_inputs[idx] = shared.results[res_idx]
                erased.append(r)

        _finalize_replace(op, array_create, new_ops, result_inputs, erased, rewriter)


def _finalize_replace(
    op: hw.ArrayGetOp,
    array_create: hw.ArrayCreateOp,
    new_ops: list[Operation],
    result_inputs: list[SSAValue],
    erased: Sequence[HardfloatOperation],
    rewriter: PatternRewriter,
) -> None:
    if all(v is result_inputs[0] for v in result_inputs):
        # Every lane folds to the same SSA value — skip the result-array.
        rewriter.replace_op(op, new_ops=new_ops, new_results=[result_inputs[0]])
    else:
        result_arr = hw.ArrayCreateOp(*result_inputs)
        new_get = hw.ArrayGetOp(result_arr.result, op.index)
        new_ops.extend([result_arr, new_get])
        rewriter.replace_op(op, new_ops=new_ops, new_results=[new_get.result])

    if not array_create.result.uses:
        rewriter.erase_op(array_create)
        for r in erased:
            if not any(res.uses for res in r.results):
                rewriter.erase_op(r)


class MergeAcrossArrayGetPass(ModulePass):
    """
    Lift shared rounders and shared muxable hardfloat ops out of the
    `array_get(array_create(...))` mutex pattern produced by
    `FinalizePhsToHWPass`.
    """

    name = "merge-across-array-get"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        patterns: list[RewritePattern] = [SinkRounder(), ShareMuxableOp()]
        PatternRewriteWalker(
            GreedyRewritePatternApplier(patterns),
            apply_recursively=False,
        ).rewrite_module(op)

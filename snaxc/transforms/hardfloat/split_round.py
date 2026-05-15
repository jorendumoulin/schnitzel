"""
Split `hardfloat.add_rec_fn` / `hardfloat.mul_rec_fn` into raw cores plus a
standalone `hardfloat.round_raw_to_rec_fn`.

Run **before** the existing `cse` pass in the hardware pipeline. Splitting
exposes the rounder as a separate op, so CSE can dedupe rounders that come
from different raw cores (e.g. one regions yields an addf result and another
a mulf result on the same recoded inputs and same rounding mode — both
rounders end up identical and collapse).
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import IntegerType, ModuleOp
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
    MulRawFnOp,
    MulRecFnOp,
    RecodeToRawOp,
    RoundRawToRecFnOp,
)


def _raw_in_type(sig: int, exp: int) -> IntegerType:
    return IntegerType(sig + exp + 7)


def _raw_out_type(sig: int, exp: int) -> IntegerType:
    return IntegerType(sig + exp + 9)


class SplitAddRecFn(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: AddRecFnOp, rewriter: PatternRewriter):
        sig = op.sig_width.data
        exp = op.exp_width.data
        rec_t = op.out.type
        raw_in_t = _raw_in_type(sig, exp)
        raw_out_t = _raw_out_type(sig, exp)

        ra = RecodeToRawOp([op.a], [raw_in_t], sig, exp)
        rb = RecodeToRawOp([op.b], [raw_in_t], sig, exp)
        core = AddRawFnOp(
            [op.subOp, ra, rb],
            [IntegerType(1), raw_out_t],
            sig,
            exp,
        )
        rounder = RoundRawToRecFnOp(
            [core.invalidExc, core.rawOut, op.roundingMode, op.detectTininess],
            [rec_t, IntegerType(5)],
            sig,
            exp,
        )
        rewriter.replace_op(
            op,
            new_ops=[ra, rb, core, rounder],
            new_results=[rounder.out, rounder.exceptionFlags],
        )


class SplitMulRecFn(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: MulRecFnOp, rewriter: PatternRewriter):
        sig = op.sig_width.data
        exp = op.exp_width.data
        rec_t = op.out.type
        raw_in_t = _raw_in_type(sig, exp)
        raw_out_t = _raw_out_type(sig, exp)

        ra = RecodeToRawOp([op.a], [raw_in_t], sig, exp)
        rb = RecodeToRawOp([op.b], [raw_in_t], sig, exp)
        core = MulRawFnOp(
            [ra, rb],
            [IntegerType(1), raw_out_t],
            sig,
            exp,
        )
        rounder = RoundRawToRecFnOp(
            [core.invalidExc, core.rawOut, op.roundingMode, op.detectTininess],
            [rec_t, IntegerType(5)],
            sig,
            exp,
        )
        rewriter.replace_op(
            op,
            new_ops=[ra, rb, core, rounder],
            new_results=[rounder.out, rounder.exceptionFlags],
        )


class SplitHardfloatRoundersPass(ModulePass):
    """
    Decompose fused `add_rec_fn` / `mul_rec_fn` ops into
    `recode_to_raw` → `*_raw_fn` → `round_raw_to_rec_fn`.
    Idempotent: ops produced by the rewrite are not themselves matched.
    """

    name = "split-hardfloat-rounders"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        PatternRewriteWalker(
            GreedyRewritePatternApplier([SplitAddRecFn(), SplitMulRecFn()]),
            apply_recursively=False,
        ).rewrite_module(op)

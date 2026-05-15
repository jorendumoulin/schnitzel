"""
Share one `AddRecFN` block between `addf` and `subf` mutex branches.

After `FinalizePhsToHWPass` inlines phs.choose regions, lanes that came
from `arith.addf` vs `arith.subf` on the same operands materialise as:

    %a0 = hardfloat.add_rec_fn<24, 8>(%false, %a, %b, %rm, %tn) : ...
    %a1 = hardfloat.add_rec_fn<24, 8>(%true,  %a, %b, %rm, %tn) : ...
    %arr = hw.array_create %a0, %a1 : i33
    %out = hw.array_get %arr[%switch] : !hw.array<2xi33>, i1

The two `add_rec_fn` ops share every operand except `subOp` (and the
`subOp` operands are the only thing distinguishing addf from subf in the
existing float→hardfloat lowering). This pass muxes the `subOp` operands
through the same switch and folds the per-lane `add_rec_fn`s into a
single shared instance.

Runs **before** `split-hardfloat-rounders` because after the split the
fused op is gone (replaced by a raw core + standalone rounder); merging
two raw cores with differing `subOp` would need the same logic at a
different op type.
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

from snaxc.dialects.hardfloat import AddRecFnOp


class ShareAddRecFnSubOp(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: hw.ArrayGetOp, rewriter: PatternRewriter):
        array_create = op.input.owner
        if not isinstance(array_create, hw.ArrayCreateOp):
            return

        adds: list[AddRecFnOp] = []
        for inp in array_create.inputs:
            d = inp.owner
            if not isinstance(d, AddRecFnOp):
                return
            # The shared op produces a single `exceptionFlags` value, so if
            # any per-lane op's flags are observed downstream we'd lose
            # information. Bail rather than silently dropping uses.
            if d.exceptionFlags.uses:
                return
            adds.append(d)

        if len(adds) < 2:
            return

        head = adds[0]
        for r in adds[1:]:
            if (
                r.sig_width.data != head.sig_width.data
                or r.exp_width.data != head.exp_width.data
                or r.a is not head.a
                or r.b is not head.b
                or r.roundingMode is not head.roundingMode
                or r.detectTininess is not head.detectTininess
            ):
                return

        # All ops agree on (a, b, rm, tininess, widths) — mux only subOp.
        subop_arr = hw.ArrayCreateOp(*[a.subOp for a in adds])
        subop_get = hw.ArrayGetOp(subop_arr.result, op.index)
        shared = AddRecFnOp(
            [subop_get.result, head.a, head.b, head.roundingMode, head.detectTininess],
            [head.out.type, IntegerType(5)],
            head.sig_width.data,
            head.exp_width.data,
        )
        rewriter.replace_op(
            op,
            new_ops=[subop_arr, subop_get, shared],
            new_results=[shared.out],
        )

        # Original array_create is now dead. Erase it and any per-lane ops
        # that lost their last user.
        if not array_create.result.uses:
            rewriter.erase_op(array_create)
            for a in adds:
                if not a.out.uses and not a.exceptionFlags.uses:
                    rewriter.erase_op(a)


class ShareAddRecFnSubOpPass(ModulePass):
    """
    Collapse a `phs.choose` mutex over `addf`/`subf` lanes into a single
    `hardfloat.add_rec_fn` whose `subOp` is muxed by the same switch.
    """

    name = "share-add-rec-fn-subop"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        PatternRewriteWalker(
            ShareAddRecFnSubOp(),
            apply_recursively=False,
        ).rewrite_module(op)

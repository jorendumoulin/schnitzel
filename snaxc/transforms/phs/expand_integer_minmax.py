"""Expand `arith.{max,min}{s,u}i` into `arith.cmpi` + `arith.select`.

`circt-opt --map-arith-to-comb` does not handle integer min/max ops, so they
must be lowered before circt-opt sees them. xdsl's `arith-expand` would do
this too, but expands additional ops we want to keep, so we do the targeted
rewrite ourselves.
"""

from xdsl.context import Context
from xdsl.dialects import arith
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)


def _expand(op: arith.MaxSIOp | arith.MinSIOp | arith.MaxUIOp | arith.MinUIOp,
            predicate: str, rewriter: PatternRewriter) -> None:
    cmp = arith.CmpiOp(op.lhs, op.rhs, predicate)
    sel = arith.SelectOp(cmp.result, op.lhs, op.rhs)
    rewriter.replace_op(op, [cmp, sel])


class ExpandMaxSI(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.MaxSIOp, rewriter: PatternRewriter):
        _expand(op, "sgt", rewriter)


class ExpandMinSI(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.MinSIOp, rewriter: PatternRewriter):
        _expand(op, "slt", rewriter)


class ExpandMaxUI(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.MaxUIOp, rewriter: PatternRewriter):
        _expand(op, "ugt", rewriter)


class ExpandMinUI(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.MinUIOp, rewriter: PatternRewriter):
        _expand(op, "ult", rewriter)


class ExpandIntegerMinMaxPass(ModulePass):
    name = "phs-expand-integer-minmax"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [ExpandMaxSI(), ExpandMinSI(), ExpandMaxUI(), ExpandMinUI()]
            ),
            apply_recursively=False,
        ).rewrite_module(op)

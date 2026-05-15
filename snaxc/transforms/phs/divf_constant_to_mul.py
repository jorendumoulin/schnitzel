from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import arith, builtin
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.utils.hints import isa


@dataclass(frozen=True)
class DivfByConstantToMul(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.DivfOp, rewriter: PatternRewriter):
        rhs_op = op.rhs.owner
        if not isinstance(rhs_op, arith.ConstantOp):
            return
        if not isa(c := rhs_op.value, builtin.FloatAttr):
            return
        denom = c.value.data
        if denom == 0.0:
            return
        recip_attr = builtin.FloatAttr(1.0 / denom, c.type)
        recip = arith.ConstantOp(recip_attr)
        mul = arith.MulfOp(op.lhs, recip, op.fastmath)
        rewriter.replace_op(op, [recip, mul])


@dataclass(frozen=True)
class PhsDivfConstantToMulPass(ModulePass):
    """Rewrite ``arith.divf %x, %const`` as ``arith.mulf %x, 1/const``.

    Assumes reciprocal accuracy is acceptable (equivalent to fastmath<arcp>).
    Targets NN-inference workloads where division by a pooling window size
    or similar constant divisor appears in the datapath.
    """

    name = "phs-divf-constant-to-mul"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        PatternRewriteWalker(DivfByConstantToMul()).rewrite_module(op)

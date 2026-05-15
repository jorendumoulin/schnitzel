"""Approximate `arith.divf %a, %b` as `%a * recip(%b)` using a bitcast trick
plus one Newton-Raphson refinement.

The approximation uses the "magic constant" identity for IEEE-754 floats: for
positive ``x``, ``bitcast<float>(K - bitcast<int>(x))`` is a rough reciprocal
of ``x``. Choosing ``K`` to minimize relative error gives ~4 bits accuracy on
its own, and a single Newton iteration ``y * (2 - x * y)`` raises that to
~8-9 bits — enough for NN softmax normalizers.

This pass is intended for environments without hardware divide support and
where the inputs are positive (which holds for softmax: the divisor is a sum
of exponentials).
"""

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

# Empirical magic constants for the reciprocal bitcast trick. The exact value
# is the one that minimizes relative error of the initial estimate before
# Newton refinement; common choices for f32 are 0x7EF311C2..0x7EF311C3.
_MAGIC_F32 = 0x7EF311C3


@dataclass(frozen=True)
class DivfToReciprocalBitcast(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.DivfOp, rewriter: PatternRewriter):
        ty = op.result.type
        if not isa(ty, builtin.Float32Type):
            return
        int_ty = builtin.IntegerType(32)

        b_as_int = arith.BitcastOp(op.rhs, int_ty)
        magic = arith.ConstantOp(builtin.IntegerAttr(_MAGIC_F32, int_ty))
        sub_int = arith.SubiOp(magic, b_as_int)
        y0 = arith.BitcastOp(sub_int, ty)

        two = arith.ConstantOp(builtin.FloatAttr(2.0, ty))
        b_y0 = arith.MulfOp(op.rhs, y0, op.fastmath)
        nr_term = arith.SubfOp(two, b_y0, op.fastmath)
        y1 = arith.MulfOp(y0, nr_term, op.fastmath)
        result = arith.MulfOp(op.lhs, y1, op.fastmath)

        rewriter.replace_op(
            op,
            [b_as_int, magic, sub_int, y0, two, b_y0, nr_term, y1, result],
        )


@dataclass(frozen=True)
class PhsDivfToReciprocalBitcastPass(ModulePass):
    """Rewrite `arith.divf %a, %b` as `%a * recip_approx(%b)` for f32."""

    name = "phs-divf-to-reciprocal-bitcast"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        PatternRewriteWalker(DivfToReciprocalBitcast()).rewrite_module(op)

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp, UnrealizedConversionCastOp, i32
from xdsl.dialects.llvm import InlineAsmOp
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from snaxc.dialects.snax import HartIdOp


class HartIdPattern(RewritePattern):
    """Implement hartid by csr instruction"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: HartIdOp, rewriter: PatternRewriter):
        csr_op = InlineAsmOp("csrr $0, mhartid", "=r", [], [i32])
        cast_op = UnrealizedConversionCastOp.get(csr_op.results, op.result_types)
        rewriter.replace_matched_op((csr_op, cast_op))


class ConvertSnaxToLlvmPass(ModulePass):
    name = "snax-to-llvm"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        PatternRewriteWalker(HartIdPattern()).rewrite_module(op)

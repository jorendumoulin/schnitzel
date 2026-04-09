from xdsl.context import Context
from xdsl.dialects import builtin, func
from xdsl.dialects.memref import DeallocOp
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.traits import SymbolTable

from snaxc.dialects import snax


class ClearL1ToFunc(RewritePattern):
    """Insert function call to clear l1"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, clear: snax.ClearL1, rewriter: PatternRewriter):
        func_call = func.CallOp("snax_clear_l1", [], [])
        func_decl = func.FuncOp.external("snax_clear_l1", [], [])

        # find module_op and insert func call
        module_op = clear
        while not isinstance(module_op, builtin.ModuleOp):
            assert (module_op := module_op.parent_op())
        SymbolTable.insert_or_update(module_op, func_decl)

        rewriter.replace_op(clear, func_call)


class EraseDeallocs(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DeallocOp, rewriter: PatternRewriter):
        rewriter.erase_op(op)


class SNAXToFunc(ModulePass):
    name = "snax-to-func"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        PatternRewriteWalker(ClearL1ToFunc()).rewrite_module(op)
        PatternRewriteWalker(EraseDeallocs()).rewrite_module(op)

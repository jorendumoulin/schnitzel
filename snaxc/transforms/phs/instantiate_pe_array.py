from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter, PatternRewriteWalker, RewritePattern, op_type_rewrite_pattern
from xdsl.rewriter import InsertPoint

from snaxc.dialects import phs
from snaxc.phs.instantiate_array import build_pe_array_body
from snaxc.phs.template_spec import TemplateSpec

BOUNDS_ATTR_NAME = "phs_array_bounds"


@dataclass(frozen=True)
class InstantiatePEArrays(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, pe: phs.PEOp, rewriter: PatternRewriter):
        if BOUNDS_ATTR_NAME not in pe.attributes:
            return

        bounds_attr = pe.attributes[BOUNDS_ATTR_NAME]
        assert isinstance(bounds_attr, builtin.DenseArrayBase)
        template_spec = TemplateSpec.derive_template_spec(pe, bounds_attr.get_values())
        array_op = build_pe_array_body(pe, template_spec)
        rewriter.insert_op(array_op, InsertPoint.after(pe))

        del pe.attributes[BOUNDS_ATTR_NAME]


@dataclass(frozen=True)
class InstantiatePEArrayPass(ModulePass):
    name = "instantiate-pe-array"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        PatternRewriteWalker(InstantiatePEArrays(), apply_recursively=False).rewrite_module(op)

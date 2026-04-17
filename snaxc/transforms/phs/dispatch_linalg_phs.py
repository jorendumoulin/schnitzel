from collections.abc import Iterable

from xdsl.context import Context
from xdsl.dialects import builtin, linalg
from xdsl.dialects.builtin import DYNAMIC_INDEX, ShapedType
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from snaxc.hw import AccContext
from snaxc.hw.phs_accelerator import PhsAccelerator
from snaxc.phs.combine import align_schemas
from snaxc.phs.decode import MappingNotFoundError, decode_abstract_graph
from snaxc.phs.encode import convert_generic_body_to_phs
from snaxc.transforms.phs.prune_unused_carries import prune_unused_carries


class DispatchLinalgPhsPattern(RewritePattern):
    """
    Dispatch kernels to accelerators based on their specified
    compute kernel template.
    """

    accelerators: Iterable[PhsAccelerator] = []

    def __init__(self, accelerators: Iterable[PhsAccelerator]) -> None:
        self.accelerators = accelerators

    @op_type_rewrite_pattern
    def match_and_rewrite(self, linalg_op: linalg.GenericOp, rewriter: PatternRewriter):
        # if already dispatched, don't dispatch again
        if linalg_op.library_call:
            return

        to_map_pe = convert_generic_body_to_phs(linalg_op, "candidate", rewriter)
        # The candidate is a single-mode encoding of one linalg op. Two alignments
        # are needed before decode_abstract_graph can pattern-match it against a
        # merged (multi-mode) abstract PE:
        #   1. Prune unused carries so single-mode parallel kernels match an
        #      abstract that also has the carry pruned.
        #   2. Widen the candidate to the abstract's schema (max pure inputs,
        #      union of paired outputs) so dead slots the abstract owns but
        #      this mode doesn't use line up by index.
        prune_unused_carries(to_map_pe)
        for accelerator in self.accelerators:
            try:
                align_schemas(to_map_pe, accelerator.pe)
                # Don't use the values, just see if it works
                decode_abstract_graph(accelerator.pe, to_map_pe)
                # set linalg op library call
                library_call = accelerator.name

                # optional streaming extension for custom operands:
                suffix = "_stream"
                # check if no dynamic operands
                for operand in (o.type for o in linalg_op.operands if isinstance(o.type, ShapedType)):
                    if DYNAMIC_INDEX in operand.get_shape():
                        suffix = ""
                        break

                library_call = library_call + suffix
                linalg_op.library_call = builtin.StringAttr(library_call)
                break
            except MappingNotFoundError:
                continue


class DispatchLinalgPHS(ModulePass):
    name = "dispatch-linalg-phs"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        assert isinstance(ctx, AccContext)
        # Get PHS accelerators from the system context
        accelerators = [acc for acc in ctx.system.iter_accelerators() if isinstance(acc, PhsAccelerator)]

        # dispatch
        PatternRewriteWalker(DispatchLinalgPhsPattern(accelerators), apply_recursively=False).rewrite_module(op)

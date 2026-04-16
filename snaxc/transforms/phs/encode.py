from xdsl.context import Context
from xdsl.dialects import builtin, linalg
from xdsl.dialects.builtin import IntegerAttr, ModuleOp
from xdsl.parser import SymbolRefAttr
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter, PatternRewriteWalker, RewritePattern, op_type_rewrite_pattern
from xdsl.rewriter import InsertPoint
from xdsl.traits import SymbolTable

from snaxc.dialects import phs
from snaxc.phs.combine import append_to_abstract_graph
from snaxc.phs.encode import convert_generic_body_to_phs

MAGIC_ATTR_NAME = "phs_acc"
BOUNDS_ATTR_NAME = "phs_array_bounds"
CARRY_NO_ATTR_NAME = "phs.carry_no"


class EncodeLinalgGeneric(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, linalg_op: linalg.GenericOp, rewriter: PatternRewriter):
        # Bail if this accelerator does not have an acc symbol
        if MAGIC_ATTR_NAME not in linalg_op.attributes:
            return

        # Bail if the acc symbol is not a SymbolRefAttr
        acc_symbol_ref = linalg_op.attributes[MAGIC_ATTR_NAME]
        if not isinstance(acc_symbol_ref, SymbolRefAttr):
            return

        # Convert the linalg body to a phs body in a pe operation
        pe = convert_generic_body_to_phs(linalg_op, acc_symbol_ref.string_value(), rewriter)

        # Number of trailing data inputs that originated from linalg `outs`
        # operands. By the encode-pass convention these are paired (positionally)
        # with the PE outputs as readWrite carries; a later cleanup pass may
        # lower this count if some carries turn out to be unused across all
        # merged modes.
        pe.attributes[CARRY_NO_ATTR_NAME] = IntegerAttr(len(linalg_op.outputs), 64)

        # Pick up optional array bounds annotation
        if BOUNDS_ATTR_NAME in linalg_op.attributes:
            pe.attributes[BOUNDS_ATTR_NAME] = linalg_op.attributes[BOUNDS_ATTR_NAME]

        # Get enclosing module_op
        toplevel = linalg_op.get_toplevel_object()
        assert isinstance(toplevel, ModuleOp), "Expect top-level IR object to be a ModuleOp"

        # Check if a PE with the current id exists
        top_table = toplevel.get_trait(SymbolTable)
        assert top_table is not None, "Could not find the top-level symbol table"
        abstract_pe = top_table.lookup_symbol(toplevel, acc_symbol_ref)
        if abstract_pe is None:
            # If a PE with this id does not exist yet, simply insert it
            rewriter.insert_op(pe, InsertPoint.at_start(toplevel.regions[0].block))
        else:
            # If a PE with this id already exists, combine it with the previous
            msg = f"Symbol for {acc_symbol_ref.string_value()} already exists, but is not a PEOp"
            assert isinstance(abstract_pe, phs.PEOp), msg
            append_to_abstract_graph(pe, abstract_pe)
            # Propagate array bounds to existing PE if not already set
            if BOUNDS_ATTR_NAME not in abstract_pe.attributes and BOUNDS_ATTR_NAME in pe.attributes:
                abstract_pe.attributes[BOUNDS_ATTR_NAME] = pe.attributes[BOUNDS_ATTR_NAME]


class PhsEncodePass(ModulePass):
    name = "phs-encode"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        PatternRewriteWalker(EncodeLinalgGeneric(), apply_recursively=False).rewrite_module(op)

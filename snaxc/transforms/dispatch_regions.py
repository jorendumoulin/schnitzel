from dataclasses import dataclass, field

from xdsl.context import Context
from xdsl.dialects import arith, builtin, scf
from xdsl.dialects.arith import ConstantOp
from xdsl.parser import IndexType
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint

from snaxc.dialects.accfg import AwaitOp, LaunchOp, NoOp, SetupOp
from snaxc.dialects.snax import HartIdOp
from snaxc.hw.acc_context import AccContext


@dataclass
class DispatchAccfgOps(RewritePattern):
    ctx: AccContext

    constants_to_pin: set[int] = field(default_factory=lambda: set())

    @op_type_rewrite_pattern
    def match_and_rewrite(self, acc_op: SetupOp | LaunchOp | AwaitOp, rewriter: PatternRewriter):
        # Get hart id of acc op
        accelerator = self.ctx.system.find_accelerator(acc_op.accelerator)
        op_hart_id = accelerator.core.hart_id
        self.constants_to_pin.add(op_hart_id)
        op_hart_id_op = ConstantOp.from_int_and_width(op_hart_id, IndexType())

        # Hart id of this core
        hart_id_op = HartIdOp()

        # Compare both ids
        cmp_op = arith.CmpiOp(op_hart_id_op, hart_id_op, "eq")

        # Insert empty scf.if
        if_op = scf.IfOp(
            cmp_op,
            acc_op.result_types,
            true_region=[yield_op := scf.YieldOp(*acc_op.results)],
            false_region=[nop := NoOp(acc_op.result_types), scf.YieldOp(nop)] if acc_op.result_types else None,
        )
        rewriter.insert_op((op_hart_id_op, hart_id_op, cmp_op, if_op), InsertPoint.before(acc_op))

        # Move acc op within scf.if
        acc_op.detach()
        for acc_result, if_result in zip(acc_op.results, if_op.results):
            acc_result.replace_uses_with_if(if_result, lambda use: use.operation is not yield_op)
        rewriter.insert_op(acc_op, InsertPoint.at_start(if_op.true_region.block))


@dataclass(frozen=True)
class DispatchRegions(ModulePass):
    """
    This transformation dispatches different accfg operations to their designated cores,
    by enclosing the dispatchable operations in an scf.if block.

    Emitted function calls are annotated with pin_to_constants, and allows one to fully specialize
    a top-level function body to a specific core.
    """

    name = "dispatch-regions"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        assert isinstance(ctx, AccContext)
        PatternRewriteWalker(DispatchAccfgOps(ctx), apply_recursively=False).rewrite_module(op)

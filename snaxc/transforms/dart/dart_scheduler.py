from dataclasses import dataclass
from typing import cast

from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.dialects.builtin import (
    AffineMapAttr,
    ArrayAttr,
    FixedBitwidthType,
    MemRefType,
)
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from snaxc.dialects import dart
from snaxc.hw import AccContext
from snaxc.hw.accelerators.tensorcore import TensorCore
from snaxc.hw.phs_accelerator import PhsAccelerator
from snaxc.ir.dart.access_pattern import Schedule, SchedulePattern
from snaxc.ir.dart.scheduler import (
    is_memory_flexible_enough,
    is_pure_output_stationary,
    scheduler,
)


@dataclass
class AutoflowScheduler(RewritePattern):
    """
    A pass to convert streaming region operations to schedules.

    Here, the operation is scheduled to an accelerator according to the accelerator template.
    """

    ctx: AccContext
    schedule_idx: int | None = None

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: dart.OperationOp, rewriter: PatternRewriter):
        assert op.accelerator is not None
        accelerator = self.ctx.system.find_accelerator(op.accelerator)
        # Both TensorCore and PhsAccelerator expose `get_template` and accept
        # the schedule algorithm. Other accelerators have no template here.
        if not isinstance(accelerator, TensorCore | PhsAccelerator):
            return
        template = accelerator.get_template(op)

        # First, run the stream scheduling algorithm
        schedule_bounds = tuple(op.get_static_pattern_bounds())
        schedule = Schedule(SchedulePattern(schedule_bounds, pattern.data) for pattern in op.patterns.data)

        schedule = schedule.canonicalize()
        element_sizes = [cast(MemRefType[FixedBitwidthType], oper.type).element_type.size for oper in op.operands]
        schedule = scheduler(
            template,
            schedule,
            extra_checks=[
                is_pure_output_stationary,
                lambda t, s: is_memory_flexible_enough(t, s, element_sizes),
            ],
        )

        schedule_op = dart.ScheduleOp(
            op.inputs,
            op.outputs,
            ArrayAttr([AffineMapAttr(s.pattern.to_affine_map()) for s in schedule]),
            rewriter.move_region_contents_to_new_regions(op.body),
            schedule[0].bounds,
            [[]],
            op.accelerator,
            op.result_types,
        )

        rewriter.replace_op(op, schedule_op)


@dataclass(frozen=True)
class DartSchedulerPass(ModulePass):
    name = "dart-scheduler"

    schedule_idx: int | None = None

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        assert isinstance(ctx, AccContext)
        PatternRewriteWalker(AutoflowScheduler(ctx, self.schedule_idx)).rewrite_module(op)

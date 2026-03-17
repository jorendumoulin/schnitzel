from collections.abc import Iterable
from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.dialects.arith import ConstantOp
from xdsl.ir import Operation
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from snaxc.dialects import snax_stream
from snaxc.dialects.accfg import AwaitOp, LaunchOp, SetupOp
from snaxc.hw import AccContext
from snaxc.hw.accelerators.dma import Dma


@dataclass
class ConvertStreamToAccfgPattern(RewritePattern):
    ctx: AccContext

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: snax_stream.StreamingRegionOp, rewriter: PatternRewriter):
        dynamic_operands = [x for x in op.dynamic_operands]
        accelerator = self.ctx.system.find_accelerator(op.accelerator)
        assert isinstance(accelerator, Dma)
        setup_ops: list[Operation] = []
        for pattern, streamer in zip(op.stride_patterns.data, accelerator.streamers.streamers):

            def get_setup_ops(val: int, param: str) -> Iterable[Operation]:
                if val == builtin.DYNAMIC_INDEX:
                    val_op = dynamic_operands.pop(0)
                else:
                    val_op = ConstantOp.from_int_and_width(val, 32)
                    yield val_op
                yield SetupOp((val_op,), (param,), accelerator.name)

            # upper bounds
            for ub, ub_param in zip(pattern.upper_bounds, streamer.ub_params(), strict=True):
                setup_ops.extend(get_setup_ops(ub.data, ub_param))

            # temporal strides
            for ub, ub_param in zip(pattern.temporal_strides, streamer.ts_params(), strict=True):
                setup_ops.extend(get_setup_ops(ub.data, ub_param))

            # spatial strides
            for ub, ub_param in zip(pattern.spatial_strides, streamer.ss_params(), strict=True):
                setup_ops.extend(get_setup_ops(ub.data, ub_param))
        c1 = ConstantOp.from_int_and_width(1, 32)
        rewriter.replace_matched_op(
            (
                *setup_ops,
                c1,
                token := LaunchOp([c1], [accelerator.launch_param()], setup_ops[-1]),
                AwaitOp(token),
            )
        )


@dataclass(frozen=True)
class ConvertStreamToAccfgPass(ModulePass):
    name = "convert-stream-to-acc"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        assert isinstance(ctx, AccContext)
        PatternRewriteWalker(ConvertStreamToAccfgPattern(ctx)).rewrite_module(op)

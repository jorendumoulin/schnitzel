from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.dialects.arith import ConstantOp
from xdsl.ir import Operation, SSAValue
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
        if not isinstance(accelerator, Dma):
            return
        setup_vals: dict[str, SSAValue | Operation] = {}
        ops_to_add: list[Operation] = []
        for operand, pattern, streamer in zip(
            (*op.inputs, *op.outputs), op.stride_patterns.data, accelerator.streamers.streamers
        ):
            # address:
            setup_vals[streamer.addr_params()] = operand

            def add_setup_op(val: int, param: str):
                if val == builtin.DYNAMIC_INDEX:
                    val_op = dynamic_operands.pop(0)
                else:
                    val_op = ConstantOp.from_int_and_width(val, 32)
                    ops_to_add.append(val_op)
                setup_vals[param] = val_op

            # upper bounds
            for ub, ub_param in zip(pattern.upper_bounds, streamer.ub_params(), strict=True):
                add_setup_op(ub.data, ub_param)

            # temporal strides
            for ts, ts_param in zip(pattern.temporal_strides, streamer.ts_params(), strict=True):
                add_setup_op(ts.data, ts_param)

            # spatial strides
            for ss, ss_param in zip(pattern.spatial_strides, streamer.ss_params(), strict=True):
                add_setup_op(ss.data, ss_param)

        # get all remaining ops from streaming op body
        body_ops = [o for o in op.body.block.ops]
        for o in body_ops:
            o.detach()

        setup_op = SetupOp(setup_vals, accelerator.name)

        c1 = ConstantOp.from_int_and_width(1, 32)
        rewriter.replace_matched_op(
            (
                *ops_to_add,
                *body_ops,
                setup_op,
                c1,
                token := LaunchOp([c1], [accelerator.launch_param()], setup_op),
                AwaitOp(token),
            )
        )


@dataclass(frozen=True)
class ConvertStreamToAccfgPass(ModulePass):
    name = "convert-stream-to-accfg"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        assert isinstance(ctx, AccContext)
        PatternRewriteWalker(ConvertStreamToAccfgPattern(ctx)).rewrite_module(op)

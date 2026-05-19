from dataclasses import dataclass
from typing import cast

import numpy as np
from numpy.typing import NDArray
from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.ir import Block, Region
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.utils.hints import isa

from snaxc.dialects import dart, snax_stream
from snaxc.dialects.accfg import SetupOp
from snaxc.hw import AccContext
from snaxc.hw.accelerators.tensorcore import TensorCore
from snaxc.hw.phs_accelerator import PhsAccelerator
from snaxc.hw.streamers.streamers import Streamer
from snaxc.ir.dart.affine_transform import AffineTransform
from snaxc.ir.tsl.stride import Stride
from snaxc.ir.tsl.tiled_stride import TiledStride


@dataclass
class ConvertStreamToSnaxStreamPattern(RewritePattern):
    """
    Convert stream access patterns (with affinemap patterns mapping the iteration
    space to memory) into actual stride pattens for SNAX Streamers, with given
    spatial and temporal strides ready to be programmed through CSRs.
    """

    ctx: AccContext

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: dart.AccessPatternOp, rewriter: PatternRewriter):
        assert op.accelerator
        accelerator = self.ctx.system.find_accelerator(op.accelerator)
        assert isinstance(accelerator, TensorCore | PhsAccelerator)
        template = accelerator.get_template(op)
        streamers = accelerator.streamers

        snax_stride_patterns: list[snax_stream.StridePattern] = []

        for operand in range(len(op.operands)):
            pattern = AffineTransform.from_affine_map(op.patterns.data[operand].data)

            # Scalar (0-rank) broadcast operand: indexing map has no result
            # dims, so no access dimensions. Emit a degenerate stride pattern
            # (zero strides on every spatial lane, no temporal dims) — the
            # streamer reads the single value once and broadcasts it across
            # the spatial unroll.
            if pattern.A.shape[0] == 0:
                spatial_strides = [0] * len(streamers[operand].spatial_dims)
                snax_stride_patterns.append(
                    snax_stream.StridePattern(
                        upper_bounds=[],
                        temporal_strides=[],
                        spatial_strides=spatial_strides,
                    )
                )
                continue

            # filter out irrelevant spatial access patterns:
            relevant: list[bool] = [True] * (pattern.num_dims - template.num_dims)
            # relevant spatial strides have a component in the template matrix
            relevant += cast(NDArray[np.bool], template[operand].pattern.A.any(axis=0).tolist())

            # Create sets of strides
            stride_list = [
                Stride(int(pattern.A[0, i]), op.bounds.data[i].value.data)
                for i in range(pattern.num_dims)
                if relevant[i]
            ]
            # maks sure the innermost step size is 1:
            stride_list.append(Stride(step=1, bound=stride_list[-1].step))

            # Resample to streamer:
            stride_list = (
                TiledStride(stride_list)
                .canonicalize()
                .resample(streamers[operand].spatial_dims + (streamers[operand].access_width,))
            ).strides

            def create_stride_pattern(streamer: Streamer, strides: list[Stride]):
                # TODO: duplicate from copy_to_dma

                # innermost stride is the inherent access width
                assert len(strides) > 1
                strides.pop()

                # should at least be able to fill the spatial strides
                spatial_dim = streamer.spatial_dim
                assert len(strides) >= streamer.spatial_dim

                # innermost are spatial strides
                spatial_strides = [x.step for x in strides[len(strides) - spatial_dim :]]
                assert isa(spatial_strides, list[int])

                # should fit in the temporal strides
                assert len(strides) <= streamer.spatial_dim + streamer.temporal_dim + 1

                # outermost are temporal stuff
                temporal_strides = [x.step for x in strides[: len(strides) - spatial_dim]]
                assert isa(temporal_strides, list[int])
                temporal_bounds = [x.bound for x in strides[: len(strides) - spatial_dim]]
                assert isa(temporal_bounds, list[int])

                # stride is outermost-> innnermost, stride pattern is innermost -> outermost
                return snax_stream.StridePattern(
                    upper_bounds=temporal_bounds[::-1] + [0] * (streamer.temporal_dim - len(temporal_bounds)),
                    temporal_strides=temporal_strides[::-1] + [0] * (streamer.temporal_dim - len(temporal_strides)),
                    spatial_strides=spatial_strides[::-1],
                )

            snax_stride_patterns.append(create_stride_pattern(streamers[operand], stride_list))

        snax_stride_patterns = [
            pattern.canonicalize().legalize(streamer)
            for (pattern, streamer) in zip(snax_stride_patterns, accelerator.streamers)
        ]

        if isinstance(accelerator, PhsAccelerator):
            # PHS lowering downstream (PhsAccelerator.convert_to_acc_ops) needs
            # the original dart.generic inside the streaming region to decode
            # PE switch values, so move the dart body wholesale (including its
            # block args carrying the stream types).
            new_body = rewriter.move_region_contents_to_new_regions(op.body)
        else:
            # Tensorcore/Dma path: drop everything except the SetupOps that
            # were embedded in the dart body.
            bops: list[SetupOp] = []
            for bop in op.body.block.ops:
                if isinstance(bop, SetupOp):
                    bop.detach()
                    bops.append(bop)
            new_body = Region(Block(bops))

        # now create snax_streaming region op
        new_op = snax_stream.StreamingRegionOp(
            inputs=op.inputs,
            outputs=op.outputs,
            stride_patterns=snax_stride_patterns,
            dynamic_operands=[],
            accelerator=op.accelerator.data,
            body=new_body,
        )

        rewriter.replace_op(op, new_op, new_op.results)


@dataclass(frozen=True)
class ConvertDartToSnaxStream(ModulePass):
    name = "convert-dart-to-snax-stream"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        assert isinstance(ctx, AccContext)
        PatternRewriteWalker(ConvertStreamToSnaxStreamPattern(ctx)).rewrite_module(op)

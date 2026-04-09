from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.arith import ConstantOp, DivUIOp, MuliOp
from xdsl.dialects.builtin import (
    DYNAMIC_INDEX,
    FixedBitwidthType,
    IndexType,
    MemRefType,
    ModuleOp,
    i32,
)
from xdsl.dialects.memref import (
    CopyOp,
    DimOp,
    ExtractAlignedPointerAsIndexOp,
)
from xdsl.ir import Block, Region
from xdsl.parser import StringAttr
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint
from xdsl.utils.hints import isa

from snaxc.dialects.accfg import SetupOp
from snaxc.dialects.snax_stream import StreamingRegionOp, StridePattern
from snaxc.hw.acc_context import AccContext
from snaxc.hw.accelerators.dma import Dma
from snaxc.hw.system import Cluster, System


def find_dma(system: System, source: StringAttr, dest: StringAttr) -> tuple[Dma, bool] | None:
    """
    Find relevant dma engine for a transfer from source to destination.
    Returns the accelerator object and a bool whether to swap source / destination,
    or None if no DMA engine is reachable from either memory.
    """

    def get_dma_acc(mem: StringAttr) -> Dma | None:
        memory = system.find_mem(mem)
        cluster = memory.parent
        if not isinstance(cluster, Cluster):
            return None
        for core in cluster.cores:
            for acc in core.accelerators:
                if isinstance(acc, Dma):
                    return acc
        return None

    # first try destination
    if (dma := get_dma_acc(dest)) is not None:
        return dma, False
    elif (dma := get_dma_acc(source)) is not None:
        return dma, True
    else:
        return None


@dataclass
class CopyToDmaPattern(RewritePattern):
    system: System

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: CopyOp, rewriter: PatternRewriter):
        # Only handling types with a known bitwidth:
        if not isa(op.source.type, MemRefType[FixedBitwidthType]):
            return
        if not isa(op.destination.type, MemRefType[FixedBitwidthType]):
            return

        # And a known memory space
        if not isinstance(source_space := op.source.type.memory_space, StringAttr):
            return
        if not isinstance(dest_space := op.destination.type.memory_space, StringAttr):
            return

        # Shapes and element types must match
        if op.source.type.get_shape() != op.destination.type.get_shape():
            return
        if (element_type := op.source.type.get_element_type()) != op.destination.type.get_element_type():
            return

        # Get relevant dma — skip if no DMA is reachable (e.g. L3→L3 copies)
        result = find_dma(self.system, source_space, dest_space)
        if result is None:
            return
        dma, reverse_ops = result

        # Compute total size of the transfer:
        total_size_op = ConstantOp.from_int_and_width(element_type.size, IndexType())
        rewriter.insert_op(total_size_op, InsertPoint.before(op))
        for dim in range(op.source.type.get_num_dims()):
            const_op = ConstantOp.from_int_and_width(dim, IndexType())
            dim_op = DimOp.from_source_and_index(op.source, const_op.result)
            total_size_op = MuliOp(total_size_op.result, dim_op.result, IndexType())
            rewriter.insert_op((const_op, dim_op, total_size_op), InsertPoint.before(op))
        # Divide this by the size of the streamer to find the required temporal stride:
        const_op = ConstantOp.from_int_and_width(dma.streamers.streamers[0].full_width, IndexType())
        total_size_op = DivUIOp(total_size_op.result, const_op.result, IndexType())
        rewriter.insert_op((const_op, total_size_op), InsertPoint.before(op))

        # Extract source and destination pointers
        source_ptr_op = ExtractAlignedPointerAsIndexOp.get(op.source)
        dest_ptr_op = ExtractAlignedPointerAsIndexOp.get(op.destination)

        if reverse_ops:
            source_ptr_op, dest_ptr_op = dest_ptr_op, source_ptr_op

        # Create simple stride patterns:
        source_streamer = dma.streamers.streamers[0]
        source_pattern = StridePattern(
            upper_bounds=[1] * (source_streamer.temporal_dims - 1) + [DYNAMIC_INDEX],
            temporal_strides=[0] * (source_streamer.temporal_dims - 1) + [source_streamer.full_width],
            spatial_strides=source_streamer.byte_offsets,
        )
        dest_streamer = dma.streamers.streamers[1]
        dest_pattern = StridePattern(
            upper_bounds=[1] * (dest_streamer.temporal_dims - 1) + [DYNAMIC_INDEX],
            temporal_strides=[0] * (dest_streamer.temporal_dims - 1) + [dest_streamer.full_width],
            spatial_strides=dest_streamer.byte_offsets,
        )

        # set other dma params directly with accfg:
        dir_val = ConstantOp.from_int_and_width(1 if reverse_ops else 0, i32)
        dir_op = SetupOp({dma.dir_param(): dir_val}, dma.name)

        # Now create streaming region op:
        new_op = StreamingRegionOp(
            inputs=[source_ptr_op.aligned_pointer],
            outputs=[dest_ptr_op.aligned_pointer],
            stride_patterns=(source_pattern, dest_pattern),
            dynamic_operands=[total_size_op, total_size_op],
            accelerator=dma.name,
            body=Region(Block([dir_val, dir_op])),
        )

        rewriter.replace_matched_op((source_ptr_op, dest_ptr_op, new_op))


@dataclass(frozen=True)
class CopyToDmaPass(ModulePass):
    """
    This pass lowers memref copies to dma calls.
    """

    name = "copy-to-dma"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        assert isinstance(ctx, AccContext)
        PatternRewriteWalker(CopyToDmaPattern(ctx.system)).rewrite_module(op)

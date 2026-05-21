from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

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
from xdsl.ir import Block, Operation, Region, SSAValue
from xdsl.parser import NoneAttr, StringAttr
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
from snaxc.dialects.tsl import TiledStridedLayoutAttr
from snaxc.hw.acc_context import AccContext
from snaxc.hw.accelerators.dma import Dma
from snaxc.hw.streamers.streamers import Streamer
from snaxc.hw.system import Cluster, System
from snaxc.ir.tsl.stride import Stride
from snaxc.ir.tsl.tiled_stride import TiledStride
from snaxc.ir.tsl.tiled_strided_layout import TiledStridedLayout


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

        # Extract source and destination pointers
        source_ptr_op = ExtractAlignedPointerAsIndexOp.get(op.source)
        dest_ptr_op = ExtractAlignedPointerAsIndexOp.get(op.destination)

        # DMA hardware: streamer[0]=TCDM (local), streamer[1]=AXI (remote).
        # The dir flag controls transfer direction (0=AXI→TCDM, 1=TCDM→AXI).
        # For L3→L1 (reverse_ops=False): L1 ptr → TCDM streamer, L3 ptr → AXI streamer
        # For L1→L3 (reverse_ops=True):  L1 ptr → TCDM streamer, L3 ptr → AXI streamer
        # So TCDM always gets the dest for L3→L1 and source for L1→L3.
        if reverse_ops:
            # L1→L3: source is L1 (TCDM), dest is L3 (AXI)
            tcdm_ptr_op, axi_ptr_op = source_ptr_op, dest_ptr_op
        else:
            # L3→L1: source is L3 (AXI), dest is L1 (TCDM)
            tcdm_ptr_op, axi_ptr_op = dest_ptr_op, source_ptr_op

        # Determine streamer patterns:
        dynamic_operands: Sequence[Operation | SSAValue]
        has_static_layout = isinstance(op.source.type.layout, TiledStridedLayoutAttr) or isinstance(
            op.destination.type.layout, TiledStridedLayoutAttr
        )
        if DYNAMIC_INDEX in op.source.type.get_shape():
            if op.source.type.layout != NoneAttr() or op.destination.type.layout != NoneAttr():
                raise NotImplementedError("Transformations not supported for dynamic transfers")
            tcdm_pattern, axi_pattern, dynamic_operands = self.dynamic_1d_patterns(op, rewriter, dma, element_type)
        elif has_static_layout:
            tcdm_pattern, axi_pattern = self.static_transform_pattern(op, rewriter, dma, element_type, reverse_ops)
            dynamic_operands = []
        else:
            # Static shape, no tiled layout — fall back to a flat 1D transfer
            # (same pattern the dynamic path produces, but the bound becomes a
            # constant derived from the static shape).
            tcdm_pattern, axi_pattern, dynamic_operands = self.dynamic_1d_patterns(op, rewriter, dma, element_type)

        # set other dma params directly with accfg:
        dir_val = ConstantOp.from_int_and_width(1 if reverse_ops else 0, i32)
        dir_op = SetupOp({dma.dir_param(): dir_val}, dma.name)

        # Now create streaming region op:
        # inputs[0] → streamer[0] (TCDM), outputs[0] → streamer[1] (AXI)
        new_op = StreamingRegionOp(
            inputs=[tcdm_ptr_op.aligned_pointer],
            outputs=[axi_ptr_op.aligned_pointer],
            stride_patterns=(tcdm_pattern, axi_pattern),
            dynamic_operands=dynamic_operands,
            accelerator=dma.name,
            body=Region(Block([dir_val, dir_op])),
        )

        rewriter.replace_op(op, (source_ptr_op, dest_ptr_op, new_op))  # both ptr ops needed for their SSA values

    def dynamic_1d_patterns(
        self, op: CopyOp, rewriter: PatternRewriter, dma: Dma, element_type: FixedBitwidthType
    ) -> tuple[StridePattern, StridePattern, Sequence[SSAValue | Operation]]:
        assert isa(op.source.type, MemRefType[FixedBitwidthType])
        # Compute total size of the transfer:
        total_size_op = ConstantOp.from_int_and_width(element_type.size, IndexType())
        rewriter.insert_op(total_size_op, InsertPoint.before(op))
        for dim in range(op.source.type.get_num_dims()):
            const_op = ConstantOp.from_int_and_width(dim, IndexType())
            dim_op = DimOp.from_source_and_index(op.source, const_op.result)
            total_size_op = MuliOp(total_size_op.result, dim_op.result, IndexType())
            rewriter.insert_op((const_op, dim_op, total_size_op), InsertPoint.before(op))
        # Divide this by the size of the streamer to find the required temporal stride:
        const_op = ConstantOp.from_int_and_width(dma.tcdm.full_width, IndexType())
        total_size_op = DivUIOp(total_size_op.result, const_op.result, IndexType())
        rewriter.insert_op((const_op, total_size_op), InsertPoint.before(op))
        # Create simple stride patterns:
        # Unused temporal dims get bound=0 (hardware skips them)
        tcdm_pattern = StridePattern(
            upper_bounds=[DYNAMIC_INDEX] + [0] * (dma.tcdm.temporal_dims - 1),
            temporal_strides=[dma.tcdm.full_width] + [0] * (dma.tcdm.temporal_dims - 1),
            spatial_strides=dma.tcdm.byte_offsets,
        )
        axi_pattern = StridePattern(
            upper_bounds=[DYNAMIC_INDEX] + [0] * (dma.axi.temporal_dims - 1),
            temporal_strides=[dma.axi.full_width] + [0] * (dma.axi.temporal_dims - 1),
            spatial_strides=dma.axi.byte_offsets,
        )
        return tcdm_pattern, axi_pattern, (total_size_op, total_size_op)

    def static_transform_pattern(
        self,
        op: CopyOp,
        rewriter: PatternRewriter,
        dma: Dma,
        element_type: FixedBitwidthType,
        reverse_ops: bool,
    ) -> tuple[StridePattern, StridePattern]:
        # extract layout attributes
        tcdm_op, axi_op = (op.source, op.destination) if reverse_ops else (op.destination, op.source)
        assert isa(axi_op.type, MemRefType[FixedBitwidthType])
        assert isa(tcdm_op.type, MemRefType[FixedBitwidthType])
        axi_layout = axi_op.type.layout
        tcdm_layout = tcdm_op.type.layout

        # construct tiled strided layouts with equal tile size
        if not isinstance(tcdm_layout, TiledStridedLayoutAttr):
            assert isa(strides := tcdm_op.type.get_strides(), Sequence[int])
            assert isinstance(axi_layout, TiledStridedLayoutAttr)
            tcdm_layout = TiledStridedLayoutAttr(
                TiledStridedLayout.from_strides(strides, axi_layout.data.tile_bounds(), 0)
            )
        if not isinstance(axi_layout, TiledStridedLayoutAttr):
            assert isa(strides := axi_op.type.get_strides(), Sequence[int])
            assert isinstance(tcdm_layout, TiledStridedLayoutAttr)
            axi_layout = TiledStridedLayoutAttr(
                TiledStridedLayout.from_strides(strides, tcdm_layout.data.tile_bounds(), 0)
            )

        # extract stride pairs
        tcdm_strides = tuple(x for _, _, x in tcdm_layout.data)
        axi_strides = tuple(x for _, _, x in axi_layout.data)

        # multiply by element width:
        tcdm_strides = tuple(Stride(cast(int, x.step) * element_type.size, x.bound) for x in tcdm_strides)
        tcdm_strides += (Stride(1, element_type.size),)
        axi_strides = tuple(Stride(cast(int, x.step) * element_type.size, x.bound) for x in axi_strides)
        axi_strides += (Stride(1, element_type.size),)

        # order by axi strides
        sorted_strides = sorted(zip(tcdm_strides, axi_strides), key=lambda x: x[1].step or 0, reverse=True)
        tcdm_tiled_stride = TiledStride([x[0] for x in sorted_strides])
        axi_tiled_stride = TiledStride([x[1] for x in sorted_strides])

        # resample to spatial bounds of the streamers and create stride patterns

        def create_stride_pattern(streamer: Streamer, strides: list[Stride]):
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
            return StridePattern(
                upper_bounds=temporal_bounds[::-1] + [0] * (streamer.temporal_dim - len(temporal_bounds)),
                temporal_strides=temporal_strides[::-1] + [0] * (streamer.temporal_dim - len(temporal_strides)),
                spatial_strides=spatial_strides[::-1],
            )

        tcdm_tiled_stride = tcdm_tiled_stride.canonicalize().resample(dma.tcdm.spatial_dims + (dma.tcdm.access_width,))
        tcdm_pattern = create_stride_pattern(dma.tcdm, tcdm_tiled_stride.strides)

        axi_tiled_stride = axi_tiled_stride.canonicalize().resample(dma.axi.spatial_dims + (dma.axi.access_width,))
        axi_pattern = create_stride_pattern(dma.axi, axi_tiled_stride.strides)

        return tcdm_pattern, axi_pattern


@dataclass(frozen=True)
class CopyToDmaPass(ModulePass):
    """
    This pass lowers memref copies to dma calls.
    """

    name = "copy-to-dma"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        assert isinstance(ctx, AccContext)
        PatternRewriteWalker(CopyToDmaPattern(ctx.system)).rewrite_module(op)

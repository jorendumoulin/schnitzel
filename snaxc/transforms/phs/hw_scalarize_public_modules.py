import math
from typing import cast

from xdsl.context import Context
from xdsl.dialects import builtin, hw
from xdsl.ir import SSAValue, TypeAttribute
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter, PatternRewriteWalker, RewritePattern, op_type_rewrite_pattern
from xdsl.rewriter import InsertPoint
from xdsl.utils.hints import isa

from snaxc.phs.hw_conversion import create_shaped_hw_array, get_from_shaped_hw_array, get_shaped_hw_array_shape


def _col_major_lane_to_multi_index(lane: int, shape: tuple[int, ...]) -> tuple[int, ...]:
    """Decompose a Chisel streamer lane number into a spatial multi-index.

    Chisel's AffineAgu (see ``AffineAgu.scala``) decomposes ``outputIdx`` into
    spatial indices with the *first* spatialDimSize varying fastest::

        for (dim <- spatialDimSizes.indices) {
          val dimIndex = (outputIdx / multiplier) % dimSize
          multiplier   = multiplier * dimSize
        }

    i.e. lane k → ``idx_d = (k / prod(shape[:d])) % shape[d]``. This is the
    *col-major* order (first multi-index varies fastest), and the streamer's
    Vec output is packed in the same order — so port ``X_k`` carries the data
    at multi-index ``_col_major_lane_to_multi_index(k, shape)``.

    The PE-array body indexes into reconstructed ``hw.array`` values in
    row-major form (``array_get(arr, (d0, d1, ...))``), so a port flattened
    naively with ``itertools.product(*[range(s) for s in shape])`` (row-major)
    silently transposes the data on 2D+ shapes — d0=1,d1=0 ends up wired to
    Chisel's lane for d0=0,d1=1. Iterating col-major here keeps the SV port
    names aligned with what the Chisel periphery actually drives.
    """
    multi: list[int] = []
    rem = lane
    for s in shape:
        multi.append(rem % s)
        rem //= s
    return tuple(multi)


def _multi_index_to_row_major(multi: tuple[int, ...], shape: tuple[int, ...]) -> int:
    r = 0
    for d, s in zip(multi, shape, strict=True):
        r = r * s + d
    return r


class ScalarizeHwModules(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: hw.HWModuleOp, rewriter: PatternRewriter):
        # Only work on public modules
        if op.sym_visibility is not None:
            return
        block = op.body.block

        # ── 1. Build new port list and replace array input args ──────────
        new_ports: list[hw.ModulePort] = []
        insert_offset: int = 0
        for port in op.module_type.ports:
            if port.dir.data != hw.Direction.INPUT or not isa(port.type, hw.ArrayType):
                new_ports.append(port)
                insert_offset += 1
                continue

            shape, el_type = get_shaped_hw_array_shape(port.type)
            flat_size = math.prod(shape)
            shape_t = tuple(shape)

            # Insert one scalar block arg per Chisel lane, named ``X_k``.
            # Lane k corresponds to multi-index col_major_lane_to_multi(k).
            old_arg = block.args[insert_offset]
            scalar_args_by_lane: list[SSAValue] = []
            for lane in range(flat_size):
                scalar_args_by_lane.append(rewriter.insert_block_argument(block, insert_offset + lane, el_type))

            # Reorder into row-major order so ``create_shaped_hw_array`` (which
            # is row-major: ``array_get(arr, (d0, d1, ...)) = args[d0*S1*S2+...+d1*S2+...]``)
            # makes ``array_get(arr, multi)`` return the lane that actually carries
            # the data for ``multi`` on the Chisel side.
            args_row_major: list[SSAValue | None] = [None] * flat_size
            for lane in range(flat_size):
                multi = _col_major_lane_to_multi_index(lane, shape_t)
                args_row_major[_multi_index_to_row_major(multi, shape_t)] = scalar_args_by_lane[lane]
            assert all(a is not None for a in args_row_major)

            reconst_ops, reconst_val = create_shaped_hw_array(cast(list[SSAValue], args_row_major), shape_t)
            rewriter.insert_op(reconst_ops, InsertPoint.at_start(block))
            old_arg.replace_all_uses_with(reconst_val)
            rewriter.erase_block_argument(old_arg)

            for lane in range(flat_size):
                new_ports.append(
                    hw.ModulePort(
                        builtin.StringAttr(f"{port.port_name.data}_{lane}"),
                        cast(TypeAttribute, el_type),
                        hw.DirectionAttr(data=hw.Direction.INPUT),
                    )
                )
            insert_offset += flat_size
        # ── 2. Scalarize output ports in hw.output ───────────────────────
        output_op = block.last_op
        assert isinstance(output_op, hw.OutputOp)

        new_output_operands: list[SSAValue] = []
        new_output_ports: list[hw.ModulePort] = []

        for operand, port in zip(
            output_op.operands, [p for p in op.module_type.ports if p.dir.data == hw.Direction.OUTPUT]
        ):
            if not isa(operand.type, hw.ArrayType):
                new_output_operands.append(operand)
                new_output_ports.append(port)
                continue

            shape, el_type = get_shaped_hw_array_shape(operand.type)
            shape_t = tuple(shape)
            flat_size = math.prod(shape_t)

            # Emit one scalar port per Chisel lane, in col-major order so the
            # periphery's ``out_X_k := bits(k)`` wiring drives the correct
            # multi-index. ``itertools.product`` would give row-major, which
            # silently transposes 2D+ outputs (the ``streamer_phs_2d_bcast``
            # kernel reproduces this).
            for lane in range(flat_size):
                multi = _col_major_lane_to_multi_index(lane, shape_t)
                get_ops, scalar_val = get_from_shaped_hw_array(cast(SSAValue[hw.ArrayType], operand), multi)
                rewriter.insert_op(get_ops, InsertPoint(block, insert_before=output_op))
                new_output_operands.append(scalar_val)
                new_output_ports.append(
                    hw.ModulePort(
                        builtin.StringAttr(f"{port.port_name.data}_{lane}"),
                        cast(TypeAttribute, el_type),
                        hw.DirectionAttr(data=hw.Direction.OUTPUT),
                    )
                )

        rewriter.replace_op(output_op, hw.OutputOp(new_output_operands))

        # ── 3. Update module type ─────────────────────────────────────────
        all_new_ports = [p for p in new_ports if p.dir.data != hw.Direction.OUTPUT] + new_output_ports
        op.module_type = hw.ModuleType(builtin.ArrayAttr(all_new_ports))


class HwScalarizePublicModulesPass(ModulePass):
    name = "hw-scalarize-public-modules"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        PatternRewriteWalker(ScalarizeHwModules(), apply_recursively=False).rewrite_module(op)

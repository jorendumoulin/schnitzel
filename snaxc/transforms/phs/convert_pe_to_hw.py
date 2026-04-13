from dataclasses import dataclass
from typing import cast

from xdsl.context import Context
from xdsl.dialects import builtin, hw
from xdsl.ir import BlockArgument, SSAValue, TypeAttribute
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter, PatternRewriteWalker, RewritePattern, op_type_rewrite_pattern
from xdsl.rewriter import InsertPoint

from xdsl.traits import SymbolTable

from snaxc.dialects import phs
from snaxc.phs.hw_conversion import get_pe_port_decl, get_switch_bitwidth


@dataclass(frozen=True)
class ConvertPeOps(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, pe: phs.PEOp, rewriter: PatternRewriter):
        ports_attr = get_pe_port_decl(pe)
        mod_type = hw.ModuleType(ports_attr)
        hw_mod = hw.HWModuleOp(sym_name=pe.name_prop, module_type=mod_type, body=pe.body.clone(), visibility="private")
        rewriter.replace_op(pe, [hw_mod])

        # Fix type mismatch in switch type conversion
        data_opnd_idx = len(pe.data_operands())
        switch_idx = len(pe.get_switches())

        # Create insertion point
        block = hw_mod.regions[0].block
        assert block.ops.first is not None
        ip = InsertPoint(block=block, insert_before=block.ops.first)

        # Insert casts from IntegerType to IndexType for switches
        for block_arg in block.args[data_opnd_idx : data_opnd_idx + switch_idx]:
            bitwidth = get_switch_bitwidth(block_arg)
            block_arg_index = block_arg.index
            ssaval = block.insert_arg(builtin.IntegerType(bitwidth), block_arg_index)
            op, res = builtin.UnrealizedConversionCastOp.cast_one(ssaval, builtin.IndexType())
            rewriter.replace_all_uses_with(block_arg, res)
            rewriter.insert_op(op, insertion_point=ip)
            block.erase_arg(block_arg)

        # Replace yield_op with output_op
        yield_op = block.ops.last
        assert isinstance(yield_op, phs.YieldOp)
        output_op = hw.OutputOp(yield_op.operands)
        rewriter.replace_op(yield_op, output_op)


@dataclass(frozen=True)
class ConvertPEArrayOps(RewritePattern):
    """Convert PEArrayOp to hw.module by converting instances and yield."""

    module: builtin.ModuleOp

    @op_type_rewrite_pattern
    def match_and_rewrite(self, array_op: phs.PEArrayOp, rewriter: PatternRewriter):
        # Find the first PEInstanceOp to determine switch types from the target PE module
        first_instance = next(
            (op for op in array_op.body.ops if isinstance(op, phs.PEInstanceOp)), None
        )
        switch_port_types: list[TypeAttribute] = []
        if first_instance is not None:
            switch_port_types = _get_switch_port_types(
                self.module, first_instance.pe_ref.string_value()
            )

        # Build hw port declaration, converting switch ports from index to correct int type
        ports: list[hw.ModulePort] = []
        block = array_op.body.block

        # Track which block args are switch ports (IndexType args that feed instances)
        switch_arg_type_map: dict[int, TypeAttribute] = {}
        if first_instance is not None:
            # Find which block args are used as switches by looking at the first instance
            for sw_idx, switch in enumerate(first_instance.switches):
                if isinstance(switch, BlockArgument) and sw_idx < len(switch_port_types):
                    switch_arg_type_map[switch.index] = switch_port_types[sw_idx]

        for i, arg in enumerate(block.args):
            port_type = switch_arg_type_map.get(i, cast(TypeAttribute, arg.type))
            ports.append(
                hw.ModulePort(
                    builtin.StringAttr(f"in_{i}"),
                    port_type,
                    hw.DirectionAttr(data=hw.Direction.INPUT),
                )
            )

        yield_op = array_op.get_terminator()
        for i, opnd in enumerate(yield_op.operands):
            ports.append(
                hw.ModulePort(
                    builtin.StringAttr(f"out_{i}"),
                    cast(TypeAttribute, opnd.type),
                    hw.DirectionAttr(data=hw.Direction.OUTPUT),
                )
            )

        mod_type = hw.ModuleType(builtin.ArrayAttr(ports))
        hw_mod = hw.HWModuleOp(
            sym_name=array_op.name_prop,
            module_type=mod_type,
            body=array_op.body.clone(),
        )
        rewriter.replace_op(array_op, [hw_mod])

        # Convert switch block args from IndexType to IntegerType
        hw_block = hw_mod.regions[0].block
        assert hw_block.ops.first is not None
        ip = InsertPoint(block=hw_block, insert_before=hw_block.ops.first)

        for arg_idx, int_type in switch_arg_type_map.items():
            block_arg = hw_block.args[arg_idx]
            new_arg = hw_block.insert_arg(int_type, arg_idx)
            cast_op, cast_res = builtin.UnrealizedConversionCastOp.cast_one(
                new_arg, builtin.IndexType()
            )
            rewriter.replace_all_uses_with(block_arg, cast_res)
            rewriter.insert_op(cast_op, insertion_point=ip)
            hw_block.erase_arg(block_arg)

        # Convert phs.instance -> hw.instance inside the body,
        # looking up the target PE hw.module to get correct switch types
        for op in list(hw_block.ops):
            if isinstance(op, phs.PEInstanceOp):
                _convert_pe_instance(op, rewriter, self.module)

        # Replace phs.yield with hw.output
        hw_yield = hw_block.ops.last
        assert isinstance(hw_yield, phs.YieldOp)
        output_op = hw.OutputOp(hw_yield.operands)
        rewriter.replace_op(hw_yield, output_op)


def _get_switch_port_types(module: builtin.ModuleOp, pe_ref: str) -> list[TypeAttribute]:
    """Look up the PE's hw.module to get the actual switch port types."""
    pe_mod = SymbolTable.lookup_symbol(module, pe_ref)
    if not isinstance(pe_mod, hw.HWModuleOp):
        return []
    switch_types: list[TypeAttribute] = []
    for port in pe_mod.module_type.ports:
        if port.dir.data == hw.Direction.INPUT and "switch" in port.port_name.data:
            switch_types.append(port.type)
    return switch_types


def _convert_pe_instance(
    instance: phs.PEInstanceOp, rewriter: PatternRewriter, module: builtin.ModuleOp
):
    """Convert a phs.instance to hw.instance, casting switch types to match the PE module."""
    in_port_list: list[tuple[str, SSAValue]] = []
    out_port_list: list[tuple[str, TypeAttribute]] = []

    for i, data_opnd in enumerate(instance.data_operands):
        in_port_list.append((f"data_{i}", data_opnd))

    # Look up the target PE module to get the correct switch port types
    switch_port_types = _get_switch_port_types(module, instance.pe_ref.string_value())

    for i, switch in enumerate(instance.switches):
        if i < len(switch_port_types) and isinstance(switch.type, builtin.IndexType):
            # Cast index -> correct integer type
            cast_op, cast_res = builtin.UnrealizedConversionCastOp.cast_one(
                switch, switch_port_types[i]
            )
            rewriter.insert_op(cast_op, InsertPoint.before(instance))
            in_port_list.append((f"switch_{i}", cast_res))
        else:
            in_port_list.append((f"switch_{i}", switch))

    for i, res in enumerate(instance.res):
        out_port_list.append((f"out_{i}", cast(TypeAttribute, res.type)))

    hw_instance = hw.InstanceOp(
        instance_name=instance.instance_name.data,
        module_name=instance.pe_ref,
        inputs=in_port_list,
        outputs=out_port_list,
    )
    rewriter.replace_op(instance, hw_instance)


@dataclass(frozen=True)
class ConvertPEToHWPass(ModulePass):
    name = "convert-pe-to-hw"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        PatternRewriteWalker(ConvertPeOps(), apply_recursively=False).rewrite_module(op)
        PatternRewriteWalker(ConvertPEArrayOps(module=op), apply_recursively=False).rewrite_module(op)

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.dialects.arith import ConstantOp, IndexCastOp
from xdsl.dialects.llvm import InlineAsmOp
from xdsl.ir import Operation
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint

from snaxc.dialects import accfg
from snaxc.hw import AccContext
from snaxc.hw.accelerators.dma import Dma
from snaxc.hw.system import System


@dataclass
class LowerAccfgSetupLaunchToCsr(RewritePattern):
    """
    Convert launch / setup ops to a series of CSR sets that set each field to the given value.
    """

    system: System

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: accfg.SetupOp | accfg.LaunchOp, rewriter: PatternRewriter) -> None:
        accelerator = self.system.find_accelerator(op.accelerator)
        assert isinstance(accelerator, Dma)
        field_to_csr = accelerator.param_values()
        ops: dict[int, list[Operation]] = {}
        for field, val in op.iter_params():
            addr = field_to_csr[field]
            ops[addr] = []
            if isinstance(val.type, builtin.IndexType):
                val_to_i32 = IndexCastOp(val, builtin.i32)
                ops[addr].append(val_to_i32)
                val = val_to_i32.result
            ops[addr].append(InlineAsmOp(f"csrw {addr:#x}, $0", "rK", [val], has_side_effects=True))
        # order ops by csr addr
        sorted_ops: list[Operation] = []
        for key in sorted(ops):
            sorted_ops.extend(ops[key])
        rewriter.insert_op(sorted_ops, InsertPoint.before(op))
        rewriter.erase_op(op)


@dataclass
class LowerAccfgAwaitToCsr(RewritePattern):
    """
    Lower await ops to a set of assembly that lowers to a buffer.
    """

    system: System

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: accfg.AwaitOp, rewriter: PatternRewriter, /):
        assert isinstance(op.token.owner, accfg.LaunchOp)
        accelerator = self.system.find_accelerator(op.token.owner.accelerator)
        assert isinstance(accelerator, Dma)
        field_to_csr = accelerator.param_values()
        c0 = ConstantOp.from_int_and_width(0, 32)
        addr = field_to_csr[accelerator.launch_param()]
        accelerator.launch_param()
        write_op = InlineAsmOp(f"csrw {addr:#x}, $0", "K", [c0.result], has_side_effects=True)
        rewriter.replace_matched_op((c0, write_op), safe_erase=False)


class DeleteAllStates(RewritePattern):
    """
    This pattern deletes all remaining SSA values that are of `accfg.state` type
    from any remaining operations.

    This is done to un-weave the `accfg.state` variables that were inserted into
    control flow operations.
    """

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter, /):
        """
        This  method is implemented in two parts, because it felt easier to argue
        about operands separately from results. This shouldn't be a big problem,
        as most operations should have either arguments *or* results of the chosen
        type but rarely both.
        """
        # bug in xDSL sometimes calls this pattern on already removed IR
        if op.parent_op() is None:
            return
        # first rewrite operands:
        if any(isinstance(operand.type, accfg.StateType) for operand in op.operands):
            # use the generic creation interface to clone the op but with fewer
            # operands:
            new_op = op.__class__.create(
                operands=[operand for operand in op.operands if not isinstance(operand.type, accfg.StateType)],
                result_types=[res.type for res in op.results],
                properties=op.properties,
                attributes=op.attributes,
                successors=op.successors,
                regions=[reg.clone() for reg in op.regions],
            )
            # replace the op
            rewriter.replace_op(op, new_op, safe_erase=False)
            op = new_op

        # then we check if any of the results are of the offending type
        if any(isinstance(result.type, accfg.StateType) for result in op.results):
            # and again, clone the op but remove the results of the offending type
            new_op = op.__class__.create(
                operands=op.operands,
                result_types=[res.type for res in op.results if not isinstance(res.type, accfg.StateType)],
                properties=op.properties,
                attributes=op.attributes,
                successors=op.successors,
                regions=[op.detach_region(reg) for reg in tuple(op.regions)],
            )
            # now we need to tell the rewriter which results to "drop" from the
            # operation. In order to do that it expects a list[SSAValue | None]
            #  that maps the old results to either:
            #  - a new result to replace it, or
            #  - `None` to signify the erasure of the result var.
            # So we construct a new list that has that structure:

            # first we create a list of reverse-order results from the new op
            new_ops_results = list(new_op.results)
            # now we iterate the old results and use either:
            #  - `None` if the old result was erased, or
            #  - `new_results.pop(0)`, which is the next result of the new results
            replace_results_by = [
                (None if isinstance(res.type, accfg.StateType) else new_ops_results.pop(0)) for res in op.results
            ]
            # and then we replace the offending operation
            rewriter.replace_op(op, new_op, new_results=replace_results_by, safe_erase=False)

        # also clean up all block arguments
        for region in op.regions:
            for block in region.blocks:
                for arg in block.args:
                    if isinstance(arg.type, accfg.StateType):
                        rewriter.erase_block_argument(arg, safe_erase=False)


class RemoveAcceleratorOps(RewritePattern):
    """
    Delete all accelerator ops after we lowered the setup ops
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: accfg.AcceleratorOp, rewriter: PatternRewriter, /):
        rewriter.erase_op(op)


class ConvertAccfgToCsrPass(ModulePass):
    """
    Converts accfg dialect ops to series of SNAX-like csr sets.
    """

    name = "convert-accfg-to-csr"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        # first lower all accfg ops and erase old SSA values
        assert isinstance(ctx, AccContext)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [
                    LowerAccfgSetupLaunchToCsr(ctx.system),
                    LowerAccfgAwaitToCsr(ctx.system),
                ]
            ),
            walk_reverse=True,
        ).rewrite_module(op)

        # # then we remove all the top-level accfg.accelerator operations from the module and erase the state variables
        # PatternRewriteWalker(GreedyRewritePatternApplier([DeleteAllStates(), RemoveAcceleratorOps()])).rewrite_module(
        #     op
        # )

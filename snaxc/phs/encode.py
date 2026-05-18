from xdsl.dialects.builtin import DenseArrayBase, FunctionType, i64
from xdsl.dialects.linalg.ops import GenericOp as LinalgGenericOp
from xdsl.dialects.linalg.ops import YieldOp as LinalgYieldOp
from xdsl.ir import Block, Operation, OpResult
from xdsl.pattern_rewriter import PatternRewriter
from xdsl.traits import ConstantLike

from snaxc.dialects import dart, phs

PAIRED_OUTPUTS_ATTR_NAME = "phs.paired_outputs"


def get_id(op: Operation, count: dict[str, int]):
    """
    Use input and output types to group together operations in similar encoding spaces such that e.g.:
    e.g. the second encountered op with in0 : i32 in1 : i32 and out0 : f32 is be assigned to id
    "i_i32_i32_o_f32"
    """
    key = "i_"
    for opnd in op.operands:
        key += f"{opnd.type}_"

    key += "o_"
    for res in op.results:
        key += f"{res.type}_"

    if key in count:
        current_count = count[key] + 1
        count[key] = current_count
        return key + str(current_count)
    else:
        count[key] = 0
        return key + "0"


def convert_generic_body_to_phs(
    generic_op: LinalgGenericOp | dart.GenericOp, name: str, rewriter: PatternRewriter
) -> phs.PEOp:
    """
    Perform conversion from linalg.generic body -> phs body
                              dart.generic body -> phs body
    """

    count: dict[str, int] = {}

    # Get a copy for conversion of the block
    body_copy = generic_op.body.clone()

    # Sink outer-scope `ConstantLike` operands into the body. Each `phs.choose`
    # built below exposes its op's operands as top-level data inputs; when one
    # of those operands is a literal captured from the surrounding function
    # scope, the combine pass fails because the operand owner is neither a
    # block argument nor a prior `phs.choose`. Cloning the constant inside the
    # body turns it into a local literal of each `phs.choose` it ends up in,
    # which lowers naturally to a wired bit pattern in hardware.
    _sink_outer_constants(body_copy.block)

    generic_yield = body_copy.block.ops.last
    assert isinstance(generic_yield, LinalgYieldOp) or isinstance(generic_yield, dart.YieldOp)
    # Keep every block arg, including the linalg `outs` block args even when the
    # body never reads them. The PHS array convention is "every output is paired
    # with a readWrite carry input at position len(ins)+k", so the outs args must
    # stay in the PE's data ports for the pairing to be derivable structurally.
    # An optional cleanup pass can later collapse pairs whose carry is unused
    # back to a write-only streamer.

    pe = phs.PEOp(
        name,
        function_type=FunctionType.from_lists(body_copy.block.arg_types, generic_yield.operand_types),
        switch_no=0,
        region=body_copy,
    )
    # List of output indices that have a corresponding carry-input slot
    # (= came from a linalg `outs` operand). Initially every output is paired;
    # a later cleanup pass may shrink this list (and erase the matching
    # block-arg) for outputs whose carry is never read in the body.
    pe.attributes[PAIRED_OUTPUTS_ATTR_NAME] = DenseArrayBase.from_list(i64, list(range(len(generic_op.outputs))))
    for op in pe.body.ops:
        if isinstance(op, LinalgYieldOp) or isinstance(op, dart.YieldOp):
            yield_op = phs.YieldOp(op.operands[0])
            rewriter.replace_op(op, yield_op)
        else:
            id = get_id(op, count)
            choose_op = phs.ChooseOp.from_operations(
                id, op.operands, pe.add_switch(), [op], result_types=op.result_types
            )
            rewriter.replace_op(op, choose_op)

    return pe


def _sink_outer_constants(body_block: Block) -> None:
    """Clone every outer-scope `ConstantLike` operand into ``body_block``.

    Walks ``body_block``, identifies operands whose defining op lives outside
    the block and carries the `ConstantLike` trait, clones each such defining
    op once at the top of the block, and rewires uses inside the block to the
    clone. Constants are then treated like any other local op by the rest of
    the encoder.
    """
    clones: dict[OpResult, OpResult] = {}
    for op in list(body_block.ops):
        for i, opnd in enumerate(op.operands):
            if not isinstance(opnd, OpResult):
                continue
            owner = opnd.owner
            if owner.parent_block() is body_block:
                continue
            if not owner.has_trait(ConstantLike):
                continue
            clone_res = clones.get(opnd)
            if clone_res is None:
                cloned_op = owner.clone()
                first = body_block.ops.first
                assert first is not None
                body_block.insert_op_before(cloned_op, first)
                clone_res = cloned_op.results[opnd.index]
                clones[opnd] = clone_res
            op.operands[i] = clone_res

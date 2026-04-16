from xdsl.dialects import linalg
from xdsl.dialects.builtin import FunctionType, IntegerAttr
from xdsl.ir import Operation
from xdsl.pattern_rewriter import PatternRewriter

from snaxc.dialects import dart, phs

CARRY_NO_ATTR_NAME = "phs.carry_no"


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
    generic_op: linalg.GenericOp | dart.GenericOp, name: str, rewriter: PatternRewriter
) -> phs.PEOp:
    """
    Perform conversion from linalg.generic body -> phs body
                              dart.generic body -> phs body
    """

    count: dict[str, int] = {}

    # Get a copy for conversion of the block
    body_copy = generic_op.body.clone()
    generic_yield = body_copy.block.ops.last
    assert isinstance(generic_yield, linalg.YieldOp) or isinstance(generic_yield, dart.YieldOp)
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
    # Number of trailing data inputs that originated from linalg `outs`. Used
    # downstream to identify readWrite-carry pairs by position.
    pe.attributes[CARRY_NO_ATTR_NAME] = IntegerAttr(len(generic_op.outputs), 64)
    for op in pe.body.ops:
        if isinstance(op, linalg.YieldOp) or isinstance(op, dart.YieldOp):
            yield_op = phs.YieldOp(op.operands[0])
            rewriter.replace_op(op, yield_op)
        else:
            id = get_id(op, count)
            choose_op = phs.ChooseOp.from_operations(
                id, op.operands, pe.add_switch(), [op], result_types=op.result_types
            )
            rewriter.replace_op(op, choose_op)

    return pe

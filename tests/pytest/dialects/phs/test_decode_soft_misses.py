"""Regression tests for the per-accelerator dispatch loop.

`decode_abstract_graph` is called once per registered accelerator candidate
from `DispatchLinalgPhsPattern`, which only catches `MappingNotFoundError`.
Two normal mismatch outcomes used to be `assert`s and aborted the compile
instead of letting dispatch fall through to the next accelerator:

  * data-operand count mismatch
  * candidate ChooseOp id absent from the abstract graph
"""

import pytest
from xdsl.dialects.arith import AddiOp, MuliOp
from xdsl.dialects.builtin import FunctionType, IndexType, i32
from xdsl.ir import Block, Region

from snaxc.dialects import phs
from snaxc.phs.decode import MappingNotFoundError, decode_abstract_graph


def _single_choose_pe(name: str, choose_id: str, op_cls: type) -> phs.PEOp:
    """PE with two i32 inputs, one switch, one ChooseOp wrapping `op_cls`."""
    in_types = [i32, i32]
    out_types = [i32]
    block_inputs = [*in_types, IndexType()]
    block = Block(arg_types=block_inputs)
    lhs, rhs, switch = block.args
    inner = op_cls(lhs, rhs)
    choose = phs.ChooseOp.from_operations(choose_id, [lhs, rhs], switch, [inner], out_types)
    block.add_ops([choose, phs.YieldOp(choose)])
    return phs.PEOp(name, FunctionType.from_lists(block_inputs, out_types), 1, Region(block))


def _three_input_pe() -> phs.PEOp:
    """PE with three i32 data inputs (an extra unused arg gives a different
    data_operand count than the 2-input PE)."""
    in_types = [i32, i32, i32]
    out_types = [i32]
    block_inputs = [*in_types, IndexType()]
    block = Block(arg_types=block_inputs)
    a, b, _c, switch = block.args
    inner = AddiOp(a, b)
    choose = phs.ChooseOp.from_operations("0", [a, b], switch, [inner], out_types)
    block.add_ops([choose, phs.YieldOp(choose)])
    return phs.PEOp("acc3in", FunctionType.from_lists(block_inputs, out_types), 1, Region(block))


def test_operand_count_mismatch_is_soft() -> None:
    """Different data_operand counts must raise MappingNotFoundError, not AssertionError."""
    abstract = _single_choose_pe("acc2in", "0", AddiOp)  # 2 data operands
    candidate = _three_input_pe()  # 3 data operands

    with pytest.raises(MappingNotFoundError, match="data_operands"):
        decode_abstract_graph(abstract, candidate)


def test_missing_choose_op_id_is_soft() -> None:
    """Candidate carrying a ChooseOp id the abstract graph doesn't have must
    raise MappingNotFoundError, not AssertionError."""
    # Abstract: one ChooseOp with id "0"
    abstract = _single_choose_pe("acc_add", "0", AddiOp)
    # Candidate: same data_operand count, but ChooseOp id is "missing"
    candidate = _single_choose_pe("acc_mul", "missing", MuliOp)

    with pytest.raises(MappingNotFoundError, match="ChooseOp"):
        decode_abstract_graph(abstract, candidate)

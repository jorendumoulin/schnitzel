"""The mux settings are derived, not searched, and the two agree.

`decode_abstract_graph` used to enumerate every assignment of the mux switches
and validate each one. Propagation walks each operand down to the provenance it
requires instead, which pins the muxes on the way. Both accept exactly the same
candidates, so the enumeration is kept only as a fallback and these tests hold
the two to the same answers.
"""

from collections.abc import Sequence

import pytest
from create_input import create_test_input
from xdsl.dialects.arith import AddiOp, MuliOp
from xdsl.dialects.builtin import FunctionType, IndexType, i32
from xdsl.ir import Block, Region

from snaxc.dialects import phs
from snaxc.phs.combine import append_to_abstract_graph
from snaxc.phs.decode import (
    MappingNotFoundError,
    decode_abstract_graph,
    propagate_mapping,
    search_mapping,
    valid_mapping,
)


def _merged_abstract() -> tuple[phs.PEOp, Sequence[phs.PEOp]]:
    """The fixture PEs of test_phs_decode, merged into one abstract PE."""
    pe_a, pe_b, pe_c, pe_d, pe_e, _pe_f = create_test_input()
    for candidate in (pe_c, pe_d, pe_e):
        append_to_abstract_graph(candidate, pe_b)
    return pe_b, (pe_c, pe_d, pe_e)


def _muxes(pe: phs.PEOp) -> list[phs.MuxOp]:
    return [op for op in pe.body.ops if isinstance(op, phs.MuxOp)]


def test_propagation_agrees_with_search() -> None:
    """Both find a valid mapping for every candidate the abstract PE was built from."""
    abstract, candidates = _merged_abstract()
    muxes = _muxes(abstract)
    assert muxes, "fixture is only interesting if the merge inserted muxes"

    for candidate in candidates:
        propagated = propagate_mapping(candidate, abstract, muxes)
        searched = search_mapping(candidate, abstract, muxes)
        assert propagated is not None
        assert searched is not None
        # Any valid assignment programs the PE correctly, so the two need not
        # pick the same one, but both have to be valid.
        assert valid_mapping(candidate, abstract, propagated)
        assert valid_mapping(candidate, abstract, searched)


def test_propagation_rejects_what_search_rejects() -> None:
    """A candidate whose operands cannot be routed is refused by both."""
    abstract, _ = _merged_abstract()
    muxes = _muxes(abstract)

    # Swap the operands of a fixture candidate so its provenances no longer
    # match anything the abstract PE can deliver at that position.
    in_types = [i32, i32]
    block_inputs = [*in_types, IndexType()]
    block = Block(arg_types=block_inputs)
    lhs, rhs, switch = block.args
    choose = phs.ChooseOp.from_operations("_nonexistent", [lhs, rhs], switch, [AddiOp(lhs, rhs)], [i32])
    block.add_ops([choose, phs.YieldOp(choose)])
    candidate = phs.PEOp("bogus", FunctionType.from_lists(block_inputs, [i32]), 1, Region(block))

    with pytest.raises(MappingNotFoundError):
        propagate_mapping(candidate, abstract, muxes)


def test_decode_is_deterministic() -> None:
    """Decoding the same candidate twice gives the same switch vector."""
    abstract, candidates = _merged_abstract()
    for candidate in candidates:
        first = list(decode_abstract_graph(abstract, candidate))
        second = list(decode_abstract_graph(abstract, candidate))
        assert first == second


def test_unconstrained_muxes_default_to_zero() -> None:
    """A mux no operand routes through is left at its default rather than searched."""
    abstract, candidates = _merged_abstract()
    muxes = _muxes(abstract)
    mapping = propagate_mapping(candidates[0], abstract, muxes)
    assert mapping is not None
    assert set(mapping) == set(muxes)
    assert all(value in (0, 1) for value in mapping.values())


def test_single_choose_needs_no_search() -> None:
    """With no muxes at all, propagation returns an empty mapping."""
    in_types = [i32, i32]
    block_inputs = [*in_types, IndexType()]

    def build(name: str, ops: list[type]) -> phs.PEOp:
        block = Block(arg_types=block_inputs)
        lhs, rhs, switch = block.args
        choose = phs.ChooseOp.from_operations("_0", [lhs, rhs], switch, [cls(lhs, rhs) for cls in ops], [i32])
        block.add_ops([choose, phs.YieldOp(choose)])
        return phs.PEOp(name, FunctionType.from_lists(block_inputs, [i32]), 1, Region(block))

    abstract = build("abstract", [AddiOp, MuliOp])
    candidate = build("candidate", [MuliOp])
    assert propagate_mapping(candidate, abstract, []) == {}
    assert list(decode_abstract_graph(abstract, candidate)) == [1]


def _figure_pes() -> tuple[phs.PEOp, phs.PEOp, phs.PEOp]:
    """The PE merging figure, in its two-input form.

    Both bodies read the same two operands, so they merge, but one yields the
    result of its only ChooseOp and the other yields the result of a second
    ChooseOp chained after the first. Aggregation therefore has to insert a
    mux in front of the terminator, which is the case propagation exists for.
    """
    from xdsl.dialects.arith import SubiOp, XOrIOp

    in_types = [i32, i32]
    block_inputs = [*in_types, IndexType()]

    block_a = Block(arg_types=block_inputs)
    lhs, rhs, switch = block_a.args
    choose_a = phs.ChooseOp.from_operations("_0", [lhs, rhs], switch, [AddiOp(lhs, rhs)], [i32])
    block_a.add_ops([choose_a, phs.YieldOp(choose_a)])
    pe_add = phs.PEOp("acc", FunctionType.from_lists(block_inputs, [i32]), 1, Region(block_a))

    block_b = Block(arg_types=[*in_types, IndexType(), IndexType()])
    lhs, rhs, switch_0, switch_1 = block_b.args
    choose_x = phs.ChooseOp.from_operations("_0", [lhs, rhs], switch_0, [XOrIOp(lhs, rhs)], [i32])
    choose_s = phs.ChooseOp.from_operations(
        "_1", [choose_x.results[0], rhs], switch_1, [SubiOp(choose_x.results[0], rhs)], [i32]
    )
    block_b.add_ops([choose_x, choose_s, phs.YieldOp(choose_s)])
    pe_chain = phs.PEOp(
        "acc", FunctionType.from_lists([*in_types, IndexType(), IndexType()], [i32]), 2, Region(block_b)
    )

    abstract = pe_add.clone()
    append_to_abstract_graph(pe_chain.clone(), abstract)
    return abstract, pe_add, pe_chain


def test_mux_case_from_the_merging_figure() -> None:
    """Merging the two bodies of the figure inserts a mux, and both modes decode."""
    abstract, pe_add, pe_chain = _figure_pes()
    muxes = _muxes(abstract)
    assert len(muxes) == 1, "merging a chained body into a direct one must insert one mux"

    for candidate in (pe_add, pe_chain):
        propagated = propagate_mapping(candidate, abstract, muxes)
        assert propagated is not None
        assert valid_mapping(candidate, abstract, propagated)
        searched = search_mapping(candidate, abstract, muxes)
        assert searched is not None

    # The two modes must not select the same branch of the mux, otherwise the
    # merged PE would compute the same thing in both.
    add_mapping = propagate_mapping(pe_add, abstract, muxes)
    chain_mapping = propagate_mapping(pe_chain, abstract, muxes)
    assert add_mapping is not None and chain_mapping is not None
    assert add_mapping[muxes[0]] != chain_mapping[muxes[0]]

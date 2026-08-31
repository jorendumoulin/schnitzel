from collections.abc import Sequence
from typing import cast

from xdsl.dialects import arith
from xdsl.dialects.builtin import IndexType
from xdsl.ir import BlockArgument, Operation
from xdsl.irdl import Operand

from snaxc.dialects import phs
from snaxc.phs.combine import get_abstract_possibilities


class MappingNotFoundError(Exception):
    """
    An exception for when a valid mapping can not be found
    """

    pass


def valid_mapping(graph: phs.PEOp, abstract_graph: phs.PEOp, mapping: dict[phs.MuxOp, int]) -> bool:
    """
    Given an abstract_graph and its switch_values, check whether connections are made such that
    it gives equivalent behaviour to the concrete graph.

    This done by going over all operations in the graph and checking whether
    the connections to the data operands made are coming from the same choose_op, or index in the PEOp.

    Connections to switches can not be checked; concrete graphs and abstract graphs are not guaranteed to have
    the same number of switches.

    Returns True if the connections are equivalent and false otherwise
    """

    # This function is necessary to recursively go through muxes given a mapping
    def _follow_operand(operand: Operand, mapping: dict[phs.MuxOp, int]) -> str | int:
        """
        Given a mapping for the muxes, follow the value through the mux operation

        Note: If this method is used on PE in which the muxes are not defined a KeyError will be raised!
        """
        if isinstance(operand, BlockArgument):
            return operand.index
        elif isinstance(operand.owner, phs.ChooseOp):
            return operand.owner.name_prop.data
        elif isinstance(operand.owner, phs.MuxOp):
            if mapping[operand.owner] == 1:
                return _follow_operand(operand.owner.rhs, mapping)
            else:
                return _follow_operand(operand.owner.lhs, mapping)
        else:
            raise NotImplementedError()

    # Walk the operations and check whether all data_operands are coming from the same places
    for operation in graph.body.ops:
        if isinstance(operation, phs.ChooseOp):
            op = operation
            abst_op = abstract_graph.get_choose_op(op.name_prop.data)
            if abst_op is None:
                raise MappingNotFoundError(f"Could not find equivalent ChooseOp for id {op.name_prop.data}")
        elif isinstance(operation, phs.YieldOp):
            op = operation
            abst_op = abstract_graph.get_terminator()
        else:
            raise NotImplementedError("Only expect ChooseOps and YieldOps in concrete graph")

        # Check if data_operands are similar, don't care about switches
        for opnd, abst_opnd in zip(op.data_operands, abst_op.data_operands, strict=True):
            # If it is a BlockArgument, check whether the index is the same
            if isinstance(opnd, BlockArgument):
                if opnd.index == _follow_operand(abst_opnd, mapping):
                    continue
                else:
                    return False
            # If its owner is a choose_op, check whether the name is the same
            if isinstance(opnd.owner, phs.ChooseOp):
                if opnd.owner.name_prop.data == _follow_operand(abst_opnd, mapping):
                    continue
                else:
                    return False
            else:
                raise NotImplementedError("Only expect ChooseOps or BlockArgs as operands in concrete graph")

    # If nothing failed, the mappings are equal
    return True


class AmbiguousMappingError(Exception):
    """Raised when a mux tree offers the same provenance on both of its branches.

    `uncollide_inputs` only ever adds a branch for a provenance that is not
    already reachable, so the leaves of a mux tree carry distinct provenances
    and this cannot happen. It is caught rather than propagated so that a
    future pass that breaks the invariant degrades to the search instead of
    producing a wrong mapping.
    """

    pass


def _concrete_provenance(operand: Operand) -> str | int:
    """The provenance token the abstract side has to deliver for this operand."""
    if isinstance(operand, BlockArgument):
        return operand.index
    if isinstance(operand.owner, phs.ChooseOp):
        return operand.owner.name_prop.data
    raise NotImplementedError("Only expect ChooseOps or BlockArgs as operands in concrete graph")


def _constrain(operand: Operand, provenance: str | int, mapping: dict[phs.MuxOp, int]) -> bool:
    """Force the muxes on the path from `operand` to `provenance`.

    The leaves of a mux tree carry distinct provenances, so at most one branch
    of each mux can deliver the one asked for and the path down to it is
    unique. Walking it fixes every mux on the way and leaves the others free.

    Returns False when the provenance is not reachable, or when a mux on the
    path is already pinned the other way by an earlier operand, which are the
    two ways a candidate fails to map.
    """
    while True:
        if isinstance(operand, BlockArgument):
            return operand.index == provenance
        owner = operand.owner
        if isinstance(owner, phs.ChooseOp):
            return owner.name_prop.data == provenance
        if not isinstance(owner, phs.MuxOp):
            raise NotImplementedError()

        in_lhs = provenance in get_abstract_possibilities(owner.lhs)
        in_rhs = provenance in get_abstract_possibilities(owner.rhs)
        if in_lhs and in_rhs:
            raise AmbiguousMappingError()
        if not in_lhs and not in_rhs:
            return False
        choice = 0 if in_lhs else 1
        if mapping.setdefault(owner, choice) != choice:
            return False
        operand = owner.lhs if in_lhs else owner.rhs


def propagate_mapping(
    graph: phs.PEOp, abstract_graph: phs.PEOp, muxes: Sequence[phs.MuxOp]
) -> None | dict[phs.MuxOp, int]:
    """Derive the mux settings in a single walk instead of searching for them.

    Every operand of the concrete graph names one provenance the abstract graph
    has to deliver, and that provenance pins the muxes between the operand and
    its source. Conflicting demands on a shared mux mean no assignment can
    satisfy both, which is exactly what the search would have discovered by
    exhausting the tree.

    Muxes no operand constrains are left at 0. Returns None if the candidate
    does not map.
    """
    mapping: dict[phs.MuxOp, int] = {}

    for operation in graph.body.ops:
        if isinstance(operation, phs.ChooseOp):
            op = operation
            abst_op = abstract_graph.get_choose_op(op.name_prop.data)
            if abst_op is None:
                raise MappingNotFoundError(f"Could not find equivalent ChooseOp for id {op.name_prop.data}")
        elif isinstance(operation, phs.YieldOp):
            op = operation
            abst_op = abstract_graph.get_terminator()
        else:
            raise NotImplementedError("Only expect ChooseOps and YieldOps in concrete graph")

        for opnd, abst_opnd in zip(op.data_operands, abst_op.data_operands, strict=True):
            if not _constrain(abst_opnd, _concrete_provenance(opnd), mapping):
                return None

    for mux in muxes:
        mapping.setdefault(mux, 0)
    return mapping


def search_mapping(
    graph: phs.PEOp,
    abstract_graph: phs.PEOp,
    muxes: Sequence[phs.MuxOp],
    mapping: dict[phs.MuxOp, int] = {},
    i: int = 0,
) -> None | dict[phs.MuxOp, int]:
    """
    Search for the first valid mapping of the muxes in a backtracking fashion.

    i is the depth of the search

    If mapping is not valid, return None
    """
    if i == len(muxes):
        if valid_mapping(graph, abstract_graph, mapping):
            return mapping.copy()
        return

    mux = muxes[i]
    choices = (0, 1)  # 0 = left branch , 1 = right branch
    for choice in choices:
        mapping[mux] = choice
        sol = search_mapping(graph, abstract_graph, muxes, mapping=mapping, i=i + 1)
        # If it didn't work
        del mapping[mux]
        if sol is not None:
            return sol
    return


def decode_abstract_graph(abstract_graph: phs.PEOp, graph: phs.PEOp) -> Sequence[int]:
    """
    Convert an abstract PEOp into a call op based on a concrete PEOp

    Graph has to be concrete and has to implement the same accelerator as abstract graph.
    Both abstract_graph and concrete graph need to have the same amount of data_operands.

    To get the values for all switches in the PEOp:
    * Switches to ChooseOps are decided locally, based on their id.
      The right operation is simply chosen out of the list of ops it implements.
    * Switches to muxes are routed later (globally) with a backtracking algorithm
    """
    # Make sure the graph to be decoded is concrete
    assert graph.is_concrete(), "Given graph is not concrete, unclear what choices should be made"

    # Make sure the amount of data_operands is the same for both
    len_msg = "Expect number of data_operands to be equal, got graph:{} abstract_graph:{}"
    graph_len = len(list(graph.data_operands()))
    abstract_graph_len = len(list(abstract_graph.data_operands()))
    if graph_len != abstract_graph_len:
        raise MappingNotFoundError(len_msg.format(graph_len, abstract_graph_len))

    call_switches: list[int | phs.MuxOp] = []  # for final values
    mux_switches: list[phs.MuxOp] = []  # keep track of muxes

    for switch in abstract_graph.get_switches():
        switchee = switch.get_user_of_unique_use()
        assert switchee is not None, f"Switch does not drive one choice in the PE (got {switch.uses.get_length()} uses)"

        # Local mapping of choose_ops
        if isinstance(switchee, phs.ChooseOp):
            options = list(switchee.operations())
            single_option = len(options) == 1
            # Look up the candidate's equivalent ChooseOp by id (operand/result-type signature).
            equivalent_choice = graph.get_choose_op(switchee.name_prop.data)
            if equivalent_choice is None:
                # Candidate does not need this ChooseOp at all. Single-option
                # ChooseOps emit no switch value (constant-folded in HW);
                # multi-option ones fall back to index 0 as a "don't care".
                if not single_option:
                    call_switches.append(0)
                continue
            target_operation = list(equivalent_choice.operations())[0]
            assert isinstance(target_operation, Operation)
            for i, operation in enumerate(options):
                if type(target_operation) is type(operation):
                    # Only emit a switch value when the abstract ChooseOp has
                    # more than one option — single-option ChooseOps are
                    # constant-folded in HW so no runtime value is needed,
                    # but the op-kind check above is still required to reject
                    # candidates that would dispatch to an incompatible PE
                    # (e.g. an addi candidate matched against a xori-only PE
                    # whose ChooseOp id collided via operand-type signature).
                    if not single_option:
                        call_switches.append(i)
                    break
            # If no match happened, raise an error.
            else:
                raise MappingNotFoundError(f"Failed to map {type(target_operation)} to switch of {switchee}")

        # Collecting mux_switches for later global routing
        elif isinstance(switchee, phs.MuxOp):
            # Collect mapping decisions for later mapping
            mux_switches.append(switchee)
            call_switches.append(switchee)  # append this as a placeholder, will be replaced after global routing
        else:
            raise RuntimeError("Only ChooseOp or MuxOp can be switched")

    # Derive the mapping of the mux switches. Propagation is exact: it accepts
    # and rejects the same candidates as the search it replaces, in one walk
    # rather than in 2**len(mux_switches) trials. The search is kept as a
    # fallback for the case the propagation cannot decide, which the
    # construction of the mux trees rules out today.
    try:
        mapping = propagate_mapping(graph, abstract_graph, mux_switches)
    except AmbiguousMappingError:
        mapping = search_mapping(graph, abstract_graph, mux_switches)
    else:
        # A derived mapping that does not validate means the mux trees no
        # longer carry distinct provenances per branch, so fall back rather
        # than refuse a candidate that may still map. A candidate propagation
        # rejects outright is refused without searching: under that invariant
        # the search would exhaust the tree and reject it too.
        if mapping is not None and not valid_mapping(graph, abstract_graph, mapping):
            mapping = search_mapping(graph, abstract_graph, mux_switches)
    if mapping is None:
        raise MappingNotFoundError("Could not find valid mapping")

    # Swap MuxOp switches for their actual values
    for i, switch in enumerate(call_switches):
        if isinstance(switch, phs.MuxOp):
            call_switches[i] = mapping[switch]

    return cast(Sequence[int], call_switches)


def decode_to_call_op(abstract_graph: phs.PEOp, graph: phs.PEOp) -> Sequence[Operation]:
    call_switches = decode_abstract_graph(abstract_graph, graph)
    switch_ops = [arith.ConstantOp.from_int_and_width(switch, IndexType()) for switch in call_switches]
    # Create a new CallOp
    name = abstract_graph.name_prop.data
    data_ops = abstract_graph.data_operands()
    call = phs.CallOp(name, data_ops, switch_ops, result_types=abstract_graph.get_terminator().operand_types)
    return [*switch_ops, call]

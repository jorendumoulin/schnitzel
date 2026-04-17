from collections.abc import Sequence

from xdsl.dialects.builtin import DenseArrayBase, FunctionType, i64
from xdsl.ir import BlockArgument
from xdsl.irdl import Operand

from snaxc.dialects import phs

PAIRED_OUTPUTS_ATTR_NAME = "phs.paired_outputs"


def _paired_outputs(pe: phs.PEOp) -> tuple[int, ...]:
    attr = pe.attributes.get(PAIRED_OUTPUTS_ATTR_NAME)
    if attr is None:
        return ()
    assert isinstance(attr, DenseArrayBase)
    return tuple(int(v) for v in attr.get_values())


def _set_paired_outputs(pe: phs.PEOp, value: tuple[int, ...]) -> None:
    pe.attributes[PAIRED_OUTPUTS_ATTR_NAME] = DenseArrayBase.from_list(i64, list(value))


def _num_pure_inputs(pe: phs.PEOp) -> int:
    return len(pe.data_operands()) - len(_paired_outputs(pe))


def _widen_pure_inputs(pe: phs.PEOp, target_num_pure: int, type_donor: phs.PEOp) -> None:
    """Insert dead block args at trailing pure-input positions so the PE has
    ``target_num_pure`` pure-input slots. Carries (and switches) shift right
    but keep their role: the new args slide in BEFORE the existing carries.
    Types for the new slots come from ``type_donor``'s matching positions.
    """
    current = _num_pure_inputs(pe)
    if current >= target_num_pure:
        return
    donor_pure = _num_pure_inputs(type_donor)
    assert donor_pure >= target_num_pure, (
        f"type_donor has {donor_pure} pure inputs but need types for up to {target_num_pure}"
    )
    for pos in range(current, target_num_pure):
        arg_type = type_donor.body.block.args[pos].type
        pe.body.block.insert_arg(arg_type, pos)
    pe.function_type = FunctionType.from_lists(list(pe.body.block.arg_types), list(pe.function_type.outputs))


def _widen_paired_outputs(pe: phs.PEOp, target_paired: tuple[int, ...], type_donor: phs.PEOp) -> None:
    """Insert dead carry block args so the PE's ``paired_outputs`` equals
    ``target_paired``. New carries are inserted in positional order, with
    types drawn from ``type_donor``. The trailing-carries convention
    (carry ``k`` at position ``num_pure_inputs + k``) is preserved.
    """
    current = _paired_outputs(pe)
    if current == target_paired:
        return
    current_set = set(current)
    for k in current:
        assert k in target_paired, (
            f"widen_paired_outputs only grows the set — current {current} not a subset of target {target_paired}"
        )
    num_pure = _num_pure_inputs(pe)
    donor_pure = _num_pure_inputs(type_donor)
    donor_paired = _paired_outputs(type_donor)
    # Insert dead carries at the positions that target wants but current
    # doesn't have. We walk target in order; position for target[k] is
    # num_pure + k once we've inserted enough.
    inserted = 0
    for k, output_idx in enumerate(target_paired):
        if output_idx in current_set:
            continue
        # Find the same output_idx in donor to borrow a type from.
        assert output_idx in donor_paired, (
            f"output {output_idx} missing from both current ({current}) and donor ({donor_paired})"
        )
        donor_k = donor_paired.index(output_idx)
        arg_type = type_donor.body.block.args[donor_pure + donor_k].type
        pe.body.block.insert_arg(arg_type, num_pure + k)
        inserted += 1
    pe.function_type = FunctionType.from_lists(list(pe.body.block.arg_types), list(pe.function_type.outputs))
    _set_paired_outputs(pe, target_paired)


def align_schemas(graph: phs.PEOp, abstract_graph: phs.PEOp) -> None:
    """Before merging ``graph`` into ``abstract_graph``, widen both so they
    share a common schema: ``num_pure_inputs`` becomes the max of the two,
    and ``paired_outputs`` becomes the sorted union. Dead block args are
    inserted for slots a side doesn't already have.

    This preserves the positional convention used by ``get_equivalent_owner``
    (block-arg index lookup in ``abstract_graph``), so downstream
    ``uncollide_inputs`` naturally inserts a MuxOp on any position whose
    graph operand and abstract operand disagree — and the result maps to
    one shared hardware op plus minimal muxes.
    """
    target_num_pure = max(_num_pure_inputs(graph), _num_pure_inputs(abstract_graph))
    target_paired = tuple(sorted(set(_paired_outputs(graph)) | set(_paired_outputs(abstract_graph))))

    _widen_pure_inputs(graph, target_num_pure, type_donor=abstract_graph)
    _widen_pure_inputs(abstract_graph, target_num_pure, type_donor=graph)
    _widen_paired_outputs(graph, target_paired, type_donor=abstract_graph)
    _widen_paired_outputs(abstract_graph, target_paired, type_donor=graph)


def get_equivalent_owner(operand: Operand, abstract_graph: phs.PEOp) -> BlockArgument | phs.ChooseOp:
    """
    Get operand of an operation in graph to match to abstract_graph.

    Gives an error if the operand is not the result of a BlockArgument or a ChooseOp,
    Or if a the ChooseOp with the same ID is not found in the abstract graph
    """
    # If in the current graph the operand is a BlockArgument
    # return the BlockArgument in the abstract_graph
    if isinstance(operand, BlockArgument):
        return abstract_graph.body.block.args[operand.index]
    # If in the current graph the operand is the result of a previous choice
    # get the same choice block in the abstract graph
    elif isinstance(operand.owner, phs.ChooseOp):
        abstract_choose_op = abstract_graph.get_choose_op(operand.owner.name_prop.data)
        assert abstract_choose_op is not None, "Equivalent ChooseOp not found in Abstract Graph"
        return abstract_choose_op
    else:
        raise NotImplementedError("Only expect owners to be block arguments or ChooseOps")


def get_abstract_possibilities(operand: Operand) -> list[str | int]:
    """
    Get all possible paths on the abstract graph (goes past choose_ops)
    """
    if isinstance(operand.owner, phs.MuxOp):
        possibilities_lhs = get_abstract_possibilities(operand.owner.lhs)
        possibilities_rhs = get_abstract_possibilities(operand.owner.rhs)
        return possibilities_lhs + possibilities_rhs
    elif isinstance(operand, BlockArgument):
        return [operand.index]
    elif isinstance(operand.owner, phs.ChooseOp):
        return [operand.owner.name_prop.data]
    else:
        raise NotImplementedError("Only expect owners to be block arguments, ChooseOp or MuxOps")


def are_equivalent(operand: Operand, abstract_operand: Operand) -> bool:
    """
    Check if operand of an operation in graph matches path to abstract_graph,
    or any paths exposed by choose_ops
    """
    if isinstance(operand, BlockArgument):
        return any([operand.index == poss for poss in get_abstract_possibilities(abstract_operand)])
    elif isinstance(operand.owner, phs.ChooseOp):
        return any([operand.owner.name_prop.data == poss for poss in get_abstract_possibilities(abstract_operand)])
    else:
        return False


def uncollide_inputs(op: phs.YieldOp | phs.ChooseOp, abst_op: phs.YieldOp | phs.ChooseOp):
    """
    Check if operations are routed similarly, if they are routed differently,
    add extra inputs with mux_op operations
    """
    # Make sure all connections are equivalent, otherwise add extra connections
    abstract_graph = abst_op.parent_op()
    assert isinstance(abstract_graph, phs.PEOp)
    for i, (opnd, abst_opnd) in enumerate(zip(op.data_operands, abst_op.data_operands, strict=True)):
        if are_equivalent(opnd, abst_opnd):
            continue
        else:
            # Add a mux to the switch
            equivalent_owner = get_equivalent_owner(opnd, abstract_graph)
            mux = phs.MuxOp(
                lhs=abst_opnd,  # this is the default connection
                rhs=equivalent_owner,  # this is the conflicting connection
                switch=abstract_graph.add_switch(),  # extra switch to control input
            )
            abstract_graph.body.block.insert_op_before(mux, abst_op)
            # Reroute the new mux outcome to the abstract terminator/choose_op input
            abst_op.operands[i] = mux.results[0]


def append_to_abstract_graph(
    graph: phs.PEOp,
    abstract_graph: phs.PEOp,
):
    """
    Insert graph into abstract_graph such that abstract_graph assumes the capabilities of graph.
    If certain ChooseOp nodes in abstract_graph don't exist they are added.
    If a capability is missing from a ChooseOp, it is added.
    If operations are not routed in abstract_graph the way they are routed in graph,
    MuxOps are inserted automatically to prevent colliding inputs.
    Addition of such a MuxOp adds an extra switch to the abstract_graph's PEOp
    """
    # Align the two PEs onto a common schema first. After this both sides have
    # the same pure-input count and the same paired-outputs set (dead block
    # args filled in where a side had nothing); `get_equivalent_owner`'s
    # index-based lookup is then well-defined.
    align_schemas(graph, abstract_graph)
    for op in graph.body.ops:
        if isinstance(op, phs.ChooseOp):
            choose_op = op
            choose_op_id = choose_op.name_prop.data

            # Get the op with the same id in the other one
            abstract_choose_op = abstract_graph.get_choose_op(choose_op_id)

            # If for this id none exists yet, create a new one and fill it with the operations
            if abstract_choose_op is None:
                # create the abstract_choose_op
                equivalent_opnds: Sequence[BlockArgument | phs.ChooseOp] = []
                for data_opnd in choose_op.data_operands:
                    equivalent_opnds.append(get_equivalent_owner(data_opnd, abstract_graph))
                # Add an extra switch to the PE to control this choice
                switch = abstract_graph.add_switch()
                abstract_choose_op = phs.ChooseOp.from_operations(
                    choose_op_id, equivalent_opnds, switch, list(choose_op.operations()), choose_op.result_types
                )
                abstract_graph.body.block.insert_op_before(abstract_choose_op, abstract_graph.get_terminator())
            # If for this id a choose_op exists, make sure the right connections are there
            # then add all the operations that are not yet in the abstract choose_op
            else:
                # Make sure all types are the same
                msg = "Type of {} does not match the type of the choose_op in the abstract graph"
                for typ, abstract_typ in zip(choose_op.operand_types, abstract_choose_op.operand_types, strict=True):
                    assert type(typ) is type(abstract_typ), msg.format("operands")
                for typ, abstract_typ in zip(choose_op.result_types, abstract_choose_op.result_types, strict=True):
                    assert type(typ) is type(abstract_typ), msg.format("results")
                # Make sure all connections are equivalent, otherwise add extra connections
                uncollide_inputs(choose_op, abstract_choose_op)
                # If all connections are equivalent or muxed, add remaining missing operations
                abstract_choose_op.insert_operations(list(choose_op.operations()))

        # At this level, the only expected YieldOp is the final YieldOp a.k.a. the terminator
        elif isinstance(op, phs.YieldOp):
            # Make sure all connections are equivalent, otherwise add extra connections
            uncollide_inputs(op, abstract_graph.get_terminator())

        elif isinstance(op, phs.MuxOp):
            raise NotImplementedError("Don't expect non-abstract input graph to have choose_input ops")
        else:
            raise NotImplementedError("Only expect choose_op and yield_op in non-abstract graph")

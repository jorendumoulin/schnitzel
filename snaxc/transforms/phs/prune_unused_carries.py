"""
Prune readWrite carry-input block-args that are unused across every mode of a
merged PE.

The encode pass keeps every linalg `outs` operand as a PE data-input (the
"carry" side of a readWrite streamer) so that multiple modes can share the same
PE-array structure: a mode that doesn't need accumulation just leaves its carry
unused. Once all modes have been merged into the abstract PE, a carry that is
unused everywhere in the body is genuinely dead — keeping it would force an
extra readWrite TCDM read per cycle whose data nobody consumes. This pass drops
those carries from the PE block-args (and the corresponding `phs.carry_no`
count), so downstream lowerings emit a plain ``write`` streamer for that
output instead of a ``readWrite``.
"""

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.dialects.builtin import FunctionType, IntegerAttr
from xdsl.passes import ModulePass

from snaxc.dialects import phs

CARRY_NO_ATTR_NAME = "phs.carry_no"


def _get_carry_no(pe: phs.PEOp) -> int:
    attr = pe.attributes.get(CARRY_NO_ATTR_NAME)
    if attr is None:
        return 0
    assert isinstance(attr, IntegerAttr)
    return attr.value.data


def _set_carry_no(pe: phs.PEOp, value: int) -> None:
    pe.attributes[CARRY_NO_ATTR_NAME] = IntegerAttr(value, 64)


def prune_unused_carries(pe: phs.PEOp) -> None:
    """
    Drop trailing carry-input block-args whose use-count is zero, decrementing
    ``phs.carry_no`` accordingly. Stops at the first used carry from the
    trailing end so the positional pairing convention stays consistent.
    """
    carry_no = _get_carry_no(pe)
    if carry_no == 0:
        return

    data_operands = pe.data_operands()
    num_data = len(data_operands)
    # Carries occupy the trailing carry_no positions of data operands.
    # Walk them in reverse to keep block-arg indices stable while erasing.
    pruned = 0
    for k in reversed(range(carry_no)):
        carry_idx = num_data - carry_no + k
        block_arg = pe.body.block.args[carry_idx]
        if block_arg.uses.get_length() != 0:
            # Cannot prune from the middle of the trailing run without breaking
            # the positional pairing convention. Stop at the first used carry.
            break
        pe.body.block.erase_arg(block_arg)
        pruned += 1

    if pruned == 0:
        return

    new_input_types = list(pe.body.block.arg_types)
    pe.function_type = FunctionType.from_lists(new_input_types, list(pe.function_type.outputs))
    _set_carry_no(pe, carry_no - pruned)


@dataclass(frozen=True)
class PrunePEUnusedCarriesPass(ModulePass):
    name = "phs-prune-unused-carries"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        for region_op in op.walk():
            if isinstance(region_op, phs.PEOp):
                prune_unused_carries(region_op)

"""
Prune readWrite carry-input block-args that are unused across every mode of a
merged PE.

The encode pass keeps every linalg `outs` operand as a PE data-input (the
"carry" side of a readWrite streamer) so that multiple modes can share the same
PE-array structure: a mode that doesn't need accumulation just leaves its carry
unused. Once all modes have been merged into the abstract PE, a carry that is
unused everywhere in the body is genuinely dead — keeping it would force an
extra readWrite TCDM read per cycle whose data nobody consumes. This pass drops
those carries from the PE block-args and shrinks the ``phs.paired_outputs``
list to record which outputs still own a carry, so downstream lowerings emit a
plain ``write`` streamer for the demoted output instead of a ``readWrite``.

The paired_outputs list (one i64 per remaining carry, listing the output index
that carry feeds back into) supports pruning ANY carry — not just trailing
ones. This is what guarantees an optimal lowering: every unused carry is
dropped regardless of position.
"""

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.dialects.builtin import DenseArrayBase, FunctionType, i64
from xdsl.passes import ModulePass

from snaxc.dialects import phs

PAIRED_OUTPUTS_ATTR_NAME = "phs.paired_outputs"


def get_paired_outputs(pe: phs.PEOp) -> tuple[int, ...]:
    """List of output indices that have a corresponding carry-input slot.

    Empty (or absent attr) means "no carries" — every output is write-only.
    """
    attr = pe.attributes.get(PAIRED_OUTPUTS_ATTR_NAME)
    if attr is None:
        return ()
    assert isinstance(attr, DenseArrayBase)
    return tuple(int(v) for v in attr.get_values())


def set_paired_outputs(pe: phs.PEOp, value: tuple[int, ...]) -> None:
    pe.attributes[PAIRED_OUTPUTS_ATTR_NAME] = DenseArrayBase.from_list(i64, list(value))


def prune_unused_carries(pe: phs.PEOp) -> None:
    """
    Remove every carry-input block-arg whose use-count is zero, regardless of
    its position in the trailing carry run. Updates ``phs.paired_outputs`` so
    the remaining carries are still paired with the right outputs by position.
    """
    paired = get_paired_outputs(pe)
    if not paired:
        return

    data_operands = pe.data_operands()
    num_data = len(data_operands)
    num_carries = len(paired)
    num_pure_inputs = num_data - num_carries
    assert num_pure_inputs >= 0, f"PE has {num_data} data inputs and {num_carries} carries — invariant violated"

    # Walk carry positions in reverse so block-arg indices stay stable while
    # erasing.
    new_paired = list(paired)
    pruned = False
    for k in reversed(range(num_carries)):
        carry_block_arg = pe.body.block.args[num_pure_inputs + k]
        if carry_block_arg.uses.get_length() == 0:
            pe.body.block.erase_arg(carry_block_arg)
            del new_paired[k]
            pruned = True

    if not pruned:
        return

    new_input_types = list(pe.body.block.arg_types)
    pe.function_type = FunctionType.from_lists(new_input_types, list(pe.function_type.outputs))
    set_paired_outputs(pe, tuple(new_paired))


@dataclass(frozen=True)
class PrunePEUnusedCarriesPass(ModulePass):
    name = "phs-prune-unused-carries"

    def apply(self, ctx: Context, op: builtin.ModuleOp) -> None:
        for region_op in op.walk():
            if isinstance(region_op, phs.PEOp):
                prune_unused_carries(region_op)

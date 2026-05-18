"""Scheduling preset: assign every `linalg.generic` its own PHS accelerator.

A scheduling preset is the no-transform-dialect equivalent of a
``schedule.mlir`` file: it walks the module and annotates each
``linalg.generic`` with the ``phs_acc`` / ``phs_array_bounds`` attributes that
the encode pass keys off of.

This preset gives every unannotated ``linalg.generic`` a fresh ``@accN``
symbol, monotonically counted across the module. Generics that already carry
a ``phs_acc`` attribute are left alone — partial manual scheduling stays
intact. Yield-only generics get tagged too; the encoder turns them into a PE
with an empty body (no `phs.choose` ops), which is wasteful but lets every
linalg.generic ride the same lowering path.
"""

from xdsl.context import Context
from xdsl.dialects import linalg
from xdsl.dialects.builtin import DenseArrayBase, ModuleOp, i64
from xdsl.parser import SymbolRefAttr
from xdsl.passes import ModulePass

from snaxc.transforms.phs.encode import BOUNDS_ATTR_NAME, MAGIC_ATTR_NAME

# Hardcoded array bound until we have a reason to expose it as a sub-flag.
_DEFAULT_BOUNDS = [4]


class PhsScheduleSeparateLinalgPass(ModulePass):
    name = "phs-schedule-separate-linalg"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        counter = 0
        bounds = DenseArrayBase.from_list(i64, _DEFAULT_BOUNDS)
        for nested in op.walk():
            if not isinstance(nested, linalg.GenericOp):
                continue
            if MAGIC_ATTR_NAME in nested.attributes:
                continue
            nested.attributes[MAGIC_ATTR_NAME] = SymbolRefAttr(f"acc{counter}")
            nested.attributes[BOUNDS_ATTR_NAME] = bounds
            counter += 1

from xdsl.dialects import linalg, memref
from xdsl.ir import Operation

from snaxc.hw.acc_context import AccContext


def dispatch_to_dm(op: Operation, ctx: AccContext):
    """Rule to dispatch operations to the dm core:
    for now, this is only memref copy operations"""
    if isinstance(op, memref.CopyOp):
        return True
    return False


def dispatch_to_compute(op: Operation, ctx: AccContext):
    """
    Rule to dispatch operations to the dm core:
    for now, this is only linalg generic operations
    and streaming regions
    """
    if isinstance(op, linalg.GenericOp):
        return True
    return False

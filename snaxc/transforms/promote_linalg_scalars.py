"""Promote scalar `linalg.generic` input operands to 0-D tensors/memrefs.

Rationale
---------
Downstream lowering for streamer accelerators (set-memory-layout,
dart-layout-resolution, dart.AccessPatternOp's IRDL) assumes every operand
carries shape, layout, and an aligned pointer. A scalar SSA value (e.g. a
conv zero-point or a runtime bias) carries none of that, which forces every
downstream pass to grow a scalar branch.

Running this pass before bufferization keeps the type system uniform: every
operand of a `linalg.generic` becomes a tensor (then a memref after
bufferization), including scalars, which end up as `tensor<i32>` →
`memref<i32>` (0-D, single bank slot). All later passes speak one type and
need no scalar special-case.

The scalar's indexing map is expected to already be the zero-result
`affine_map<(...) -> ()>` broadcast — it stays unchanged. The body
block-arg type stays the underlying element type, so the body is untouched.
"""

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import builtin, memref, tensor
from xdsl.dialects.builtin import MemRefType, ModuleOp, TensorType
from xdsl.dialects.linalg.ops import GenericOp as LinalgGenericOp
from xdsl.ir import Operation, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint


def _all_memref_style(op: LinalgGenericOp) -> bool:
    """Heuristic: linalg.generic is in memref form iff at least one shaped
    operand is a memref. linalg requires homogeneous tensor- or memref-form,
    so any memref participant pins the style for the whole op."""
    for operand in op.operands:
        if isinstance(operand.type, MemRefType):
            return True
    return False


def _materialize_zero_rank_memref(scalar: SSAValue) -> tuple[tuple[Operation, ...], SSAValue]:
    """Lower a scalar SSA value to a fresh 0-D `memref<T>` holding it.

    Materialises:
        %alloca = memref.alloca() : memref<T>
        memref.store %scalar, %alloca[] : memref<T>
    """
    memref_type = MemRefType(scalar.type, ())
    alloca = memref.AllocaOp.get(scalar.type, shape=[])
    assert alloca.results[0].type == memref_type
    store = memref.StoreOp.get(scalar, alloca, [])
    return (alloca, store), alloca.results[0]


def _materialize_zero_rank_tensor(scalar: SSAValue) -> tuple[tuple[Operation, ...], SSAValue]:
    """Pre-bufferize counterpart: `tensor.from_elements %scalar : tensor<T>`."""
    tensor_type = TensorType(scalar.type, ())
    fe = tensor.FromElementsOp(scalar, result_type=tensor_type)
    return (fe,), fe.result


@dataclass
class PromoteScalarOperandsPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: LinalgGenericOp, rewriter: PatternRewriter) -> None:
        memref_style = _all_memref_style(op)
        new_ops: list[Operation] = []
        replacements: list[tuple[int, SSAValue]] = []
        for i, inp in enumerate(op.inputs):
            if isinstance(inp.type, builtin.ShapedType):
                continue
            built, value = (
                _materialize_zero_rank_memref(inp) if memref_style else _materialize_zero_rank_tensor(inp)
            )
            new_ops.extend(built)
            replacements.append((i, value))
        if not replacements:
            return
        rewriter.insert_op(new_ops, InsertPoint.before(op))
        for i, value in replacements:
            # op.operands is laid out as [inputs..., outputs...]; ins live at [0, input_count).
            op.operands[i] = value


@dataclass(frozen=True)
class PromoteLinalgScalarsPass(ModulePass):
    name = "promote-linalg-scalars"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        PatternRewriteWalker(PromoteScalarOperandsPattern()).rewrite_module(op)

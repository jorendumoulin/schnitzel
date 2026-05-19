from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.dialects.linalg.ops import GenericOp as LinalgGenericOp
from xdsl.dialects.linalg.ops import YieldOp as LinalgYieldOp
from xdsl.ir import Block, Region
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint

from snaxc.dialects import dart


# Every output is wrapped as a readWrite carry streamer. The PE body decides
# (via outs block-arg use) whether the carry is actually consumed; a later
# `phs-prune-unused-carries` pass demotes unused carries to write-only.
# No special-casing on the output producer kind is needed.
@dataclass
class StreamifyGenericOpPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: LinalgGenericOp, rewriter: PatternRewriter) -> None:
        # Only convert linalg.generics claimed by an accelerator dispatch pass
        # via the conventional `<acc>_stream` library_call marker. Unclaimed
        # generics fall through to RISC-V lowering.
        if not op.library_call:
            return
        if not op.library_call.data.endswith("_stream"):
            return
        op.library_call = StringAttr(op.library_call.data[: -len("_stream")])

        input_count = len(op.inputs)
        # Every operand becomes a streamer port. Shaped operands stream their
        # element type; scalars stream their own type as a 0-rank broadcast
        # (the existing `affine_map<(...) -> ()>` indexing map handles the
        # broadcast pattern). CSR-direct programming for compile-time constants
        # is a later lowering choice — at this IR level the model is uniform.
        streamable_input_indices = tuple(
            (index, arg.type) for index, arg in enumerate(op.body.block.args[:input_count]) if arg.uses
        )
        streamable_output_indices = tuple(
            (index + input_count, arg.type) for index, arg in enumerate(op.body.block.args[input_count:])
        )

        input_stream_types = tuple(dart.StreamType(el_type) for _, el_type in streamable_input_indices)
        result_stream_types = tuple(dart.StreamType(el_type) for _, el_type in streamable_output_indices)

        patterns = ArrayAttr(
            op.indexing_maps.data[index] for index, _ in (*streamable_input_indices, *streamable_output_indices)
        )

        streaming_region_op = dart.OperationOp(
            inputs=tuple(op.operands[index] for index, _ in streamable_input_indices),
            outputs=tuple(op.operands[index] for index, _ in streamable_output_indices),
            patterns=patterns,
            body=Region(Block(arg_types=input_stream_types + result_stream_types)),
            result_types=op.result_types,
            accelerator=op.library_call,
        )

        new_body = streaming_region_op.body.block

        new_inputs = list(op.inputs)
        for stream_index, (index, _) in enumerate(streamable_input_indices):
            new_inputs[index] = new_body.args[stream_index]

        rewriter.insert_op(
            (
                generic := dart.GenericOp(
                    new_inputs,
                    rewriter.move_region_contents_to_new_regions(op.body),
                    op.doc,
                    op.library_call,
                    result_stream_types,
                ),
                dart.YieldOp(generic.results[0]),
            ),
            InsertPoint.at_end(new_body),
        )

        assert isinstance(yield_op := generic.body.block.last_op, LinalgYieldOp)
        rewriter.replace_op(yield_op, dart.YieldOp(yield_op.operands[0]))

        rewriter.replace_op(op, streaming_region_op)


@dataclass(frozen=True)
class ConvertLinalgToDart(ModulePass):
    """
    Converts a linalg generic to a dart generic wrapped in
    a dart operation.
    """

    name = "convert-linalg-to-dart"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        del ctx
        PatternRewriteWalker(StreamifyGenericOpPattern()).rewrite_module(op)

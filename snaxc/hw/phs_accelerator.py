from collections.abc import Sequence

from xdsl.dialects import arith, builtin, linalg
from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Operation, SSAValue
from xdsl.pattern_rewriter import PatternRewriter

from snaxc.dialects import accfg, dart, phs, snax_stream
from snaxc.hw.accelerators.phs import Phs
from snaxc.hw.streamer_accelerator import StreamerAccelerator
from snaxc.hw.system import Accelerator
from snaxc.ir.dart.access_pattern import Template
from snaxc.phs.combine import align_schemas
from snaxc.phs.decode import decode_abstract_graph
from snaxc.phs.encode import convert_generic_body_to_phs
from snaxc.phs.hw_conversion import get_switch_bitwidth
from snaxc.phs.template_spec import TemplateSpec
from snaxc.transforms.phs.prune_unused_carries import prune_unused_carries


class PhsAccelerator(Accelerator, StreamerAccelerator):
    """
    Accelerator interface class for PHS accelerators.

    Wraps a Phs accelerator config with the PEOp and TemplateSpec
    needed for code generation and hardware export.
    """

    def __init__(self, pe: phs.PEOp, template_spec: TemplateSpec) -> None:
        self.pe = pe

        acc_name = pe.properties["sym_name"]
        assert isinstance(acc_name, StringAttr)
        self.name = acc_name.data

        self.template_spec = template_spec

        # Build Phs accelerator from template. "True" switches are those that
        # actually drive a MuxOp or a ChooseOp with >1 operations; dead
        # switches (ChooseOp with a single option) get cleaned up by the
        # remove-one-option-switches hardware pass. Here we mirror that
        # filter per-switch so bitwidths line up with ``true_switches`` — the
        # old code took the first N bitwidths, which broke whenever a dead
        # switch preceded a live one (common after merge's MuxOp inserts).
        true_switch_bitwidths: list[int] = []
        for sw_arg in pe.get_switches():
            if sw_arg.get_unique_use() is None:
                continue
            user = sw_arg.get_user_of_unique_use()
            assert user is not None
            if isinstance(user, phs.ChooseOp):
                if len(list(user.operations())) > 1:
                    true_switch_bitwidths.append(get_switch_bitwidth(sw_arg))
            elif isinstance(user, phs.MuxOp):
                true_switch_bitwidths.append(get_switch_bitwidth(sw_arg))
        true_switches = len(true_switch_bitwidths)
        switch_bitwidths = true_switch_bitwidths

        # For each readWrite carry slot, check whether the corresponding PE
        # block-arg is actually used in the body. If not, mark carry_used=False
        # so the Scala accelerator omits it from the writeData.valid AND.
        num_data = len(pe.data_operands())
        num_pure_inputs = num_data - template_spec.carry_no
        carry_used: list[bool] = []
        for k in range(template_spec.carry_no):
            carry_block_arg = pe.body.block.args[num_pure_inputs + k]
            carry_used.append(carry_block_arg.uses.get_length() > 0)

        self.phs = Phs.from_template(
            name=self.name,
            input_sizes=template_spec.get_input_sizes(),
            output_sizes=template_spec.get_output_sizes(),
            num_switches=true_switches,
            switch_bitwidths=switch_bitwidths,
            paired_outputs=template_spec.paired_outputs,
            carry_used=carry_used,
        )

        # Initialize StreamerAccelerator with the PHS streamer configuration
        StreamerAccelerator.__init__(self, self.phs.streamers)

    def param_values(self) -> dict[str, int]:
        return self.phs.param_values()

    def barrier_address(self) -> int:
        return self.phs.barrier_address()

    def get_switch_values(
        self, op: linalg.GenericOp | dart.GenericOp
    ) -> Sequence[tuple[Sequence[Operation], SSAValue]]:
        """Decode the PEOp graph to determine switch values for the given operation."""
        candidate_pe = convert_generic_body_to_phs(op, self.name, PatternRewriter(op))
        # Align the candidate's schema with the abstract PE so decode_abstract_graph
        # sees matching shapes: first drop any carry this mode doesn't use
        # (mirrors prune on the abstract), then widen to the abstract's
        # pure-input/paired-output schema (inserting dead slots for inputs the
        # abstract has for other modes).
        prune_unused_carries(candidate_pe)
        align_schemas(candidate_pe, self.pe)
        switch_values = decode_abstract_graph(self.pe, candidate_pe)
        ops = [arith.ConstantOp.from_int_and_width(value, 32) for value in switch_values]
        return [([op], op.results[0]) for op in ops]

    def convert_to_acc_ops(self, op: Operation) -> Sequence[Operation]:
        """Lowers the operation to a sequence of accfg setup/launch/await ops."""
        if not isinstance(op, snax_stream.StreamingRegionOp):
            return []

        args = self._generate_stream_setup_vals(op)

        ops_to_insert: list[Operation] = []
        for new_ops, _ in args:
            ops_to_insert.extend(new_ops)

        param_vals = self.phs.param_values()
        fields = list(param_vals.keys())
        launch_field = "start"

        return [
            *ops_to_insert,
            setup := accfg.SetupOp({field: val for field, (_, val) in zip(fields, args)}, self.name),
            launch_val := arith.ConstantOp(builtin.IntegerAttr(1, 5)),
            token := accfg.LaunchOp([launch_val], [launch_field], setup),
            accfg.AwaitOp(token),
        ]

    def _generate_stream_setup_vals(
        self, op: snax_stream.StreamingRegionOp
    ) -> Sequence[tuple[Sequence[Operation], SSAValue]]:
        """Generate all setup values: streamer configs + switch values."""
        result: list[tuple[Sequence[Operation], SSAValue]] = []

        # The Chisel Streamer reserves a fixed number of CSR slots per
        # streamer (``temporal_dims`` ts + ``temporal_dims`` ub +
        # ``spatial_dim`` ss). The canonicalized snax_stream pattern
        # is allowed to be shorter (bound-1 dims dropped, missing spatial
        # dims for narrow-mode candidates) — if we emit fewer values here,
        # every CSR after this streamer shifts up by the missing count,
        # and the next streamer's base lands in this one's bound slot.
        # The hardware then reads garbage bounds and locks up. Pad ts/ub
        # to the streamer's declared ``temporal_dims`` (stride 0, bound 1
        # = one no-op iteration) and ss to ``spatial_dim`` (stride 0 =
        # runtime broadcast on that lane).
        for operand, pattern, streamer in zip(
            (*op.inputs, *op.outputs), op.stride_patterns.data, self.phs.streamers.streamers
        ):
            result.append(([], operand))
            ts_count = len(pattern.temporal_strides)
            ub_count = len(pattern.upper_bounds)
            ss_count = len(pattern.spatial_strides)
            for ts in pattern.temporal_strides:
                c = arith.ConstantOp.from_int_and_width(ts.data, 32)
                result.append(([c], c.result))
            for _ in range(streamer.temporal_dims - ts_count):
                c = arith.ConstantOp.from_int_and_width(0, 32)
                result.append(([c], c.result))
            for ub in pattern.upper_bounds:
                c = arith.ConstantOp.from_int_and_width(ub.data, 32)
                result.append(([c], c.result))
            for _ in range(streamer.temporal_dims - ub_count):
                c = arith.ConstantOp.from_int_and_width(1, 32)
                result.append(([c], c.result))
            for ss in pattern.spatial_strides:
                c = arith.ConstantOp.from_int_and_width(ss.data, 32)
                result.append(([c], c.result))
            for _ in range(streamer.spatial_dim - ss_count):
                c = arith.ConstantOp.from_int_and_width(0, 32)
                result.append(([c], c.result))

        generic = op.regions[0].ops.first
        assert isinstance(generic, linalg.GenericOp | dart.GenericOp)
        result.extend(self.get_switch_values(generic))

        return result

    def generate_acc_op(self) -> accfg.AcceleratorOp:
        """Generate the accfg.accelerator op with CSR address mappings."""
        param_vals = self.phs.param_values()
        launch_field = "start"
        barrier_addr = 0x900 + len(param_vals) + 1

        return accfg.AcceleratorOp(
            self.name,
            param_vals,
            {launch_field: 0x900 + len(param_vals)},
            barrier_addr,
        )

    def get_template(self, op: dart.StreamingRegionOpBase) -> Template:
        # On a multi-mode PE the unioned template covers all modes' shapes
        # together, but each dispatched kernel uses just one mode's access
        # pattern. Picking the per-mode template here lets the dart scheduler's
        # singular-vector match accept the narrower (broadcast-input) shapes
        # of modes like matmul-via-temporal-carry; runtime broadcasting is
        # handled by per-mode streamer stride config later.
        if isinstance(op, dart.OperationOp):
            operand_maps = tuple(p.data for p in op.patterns.data)
            return self.template_spec.get_dart_template_for_maps(operand_maps)
        return self.template_spec.get_dart_template()

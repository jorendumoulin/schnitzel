from collections.abc import Sequence

from xdsl.dialects import arith, builtin
from xdsl.dialects.builtin import StringAttr
from xdsl.dialects.linalg.ops import GenericOp as LinalgGenericOp
from xdsl.ir import Operation, SSAValue
from xdsl.pattern_rewriter import PatternRewriter

from snaxc.dialects import accfg, dart, phs, snax_stream
from snaxc.hw.accelerators.phs import Phs
from snaxc.hw.streamer_accelerator import StreamerAccelerator
from snaxc.hw.streamers.streamers import Streamer
from snaxc.hw.system import Accelerator
from snaxc.ir.dart.access_pattern import Schedule, Template
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

        # Build Phs accelerator from template
        true_switches = pe.get_true_switches()
        switch_bitwidths = [get_switch_bitwidth(arg) for arg in pe.get_switches() if arg.get_unique_use() is not None][
            :true_switches
        ]

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

    def get_switch_values(self, op: LinalgGenericOp | dart.GenericOp) -> Sequence[tuple[Sequence[Operation], SSAValue]]:
        """Decode the PEOp graph to determine switch values for the given operation."""
        candidate_pe = convert_generic_body_to_phs(op, self.name, PatternRewriter(op))
        # Align carry-input shape with the abstract PE (which the prune pass
        # may have shrunk after merging). Without this the candidate looks
        # wider than the abstract for parallel-only kernels.
        prune_unused_carries(candidate_pe)
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

        for operand, pattern, streamer in zip(
            (*op.inputs, *op.outputs), op.stride_patterns.data, self.phs.streamers.streamers
        ):
            result.append(([], operand))

            # The streamer reserves `streamer.temporal_dims` slots for ts/ub in
            # its CSR layout (see Phs.param_values), but convert_dart_to_snax_stream
            # may emit fewer dims (canonicalize collapses contiguous dims; the
            # bound>spat_size split branch can fold a 2D access into 1D). Pad
            # the short side with identity dims (ub=1, ts=0) so the positional
            # zip against param_values() keys stays aligned. ub=0 would mean
            # "disabled" per canonicalize semantics, which is wrong here.
            # TODO: fix convert_dart_to_snax_stream to emit T temporal dims
            # natively, then make this assert exact equality.
            ts_values = [ts.data for ts in pattern.temporal_strides]
            ub_values = [ub.data for ub in pattern.upper_bounds]
            assert len(ts_values) <= streamer.temporal_dims, (
                f"streamer '{streamer.name_base}' reserves {streamer.temporal_dims} "
                f"temporal dims but pattern has {len(ts_values)}"
            )
            pad = streamer.temporal_dims - len(ts_values)
            ts_values.extend([0] * pad)
            ub_values.extend([1] * pad)

            assert len(pattern.spatial_strides) == streamer.spatial_dim, (
                f"streamer '{streamer.name_base}' has {streamer.spatial_dim} spatial dims "
                f"but pattern has {len(pattern.spatial_strides)}"
            )

            for ts in ts_values:
                c = arith.ConstantOp.from_int_and_width(ts, 32)
                result.append(([c], c.result))
            for ub in ub_values:
                c = arith.ConstantOp.from_int_and_width(ub, 32)
                result.append(([c], c.result))
            for ss in pattern.spatial_strides:
                c = arith.ConstantOp.from_int_and_width(ss.data, 32)
                result.append(([c], c.result))

        generic = op.regions[0].ops.first
        assert isinstance(generic, LinalgGenericOp | dart.GenericOp)
        result.extend(self.get_switch_values(generic))

        return result

    def generate_acc_op(self) -> accfg.AcceleratorOp:
        """Generate the accfg.accelerator op with CSR address mappings."""
        param_vals = self.phs.param_values()
        launch_field = "start"
        base = self.phs.csr_base
        barrier_addr = base + len(param_vals) + 1

        return accfg.AcceleratorOp(
            self.name,
            param_vals,
            {launch_field: base + len(param_vals)},
            barrier_addr,
        )

    def get_template(self, op: dart.StreamingRegionOpBase) -> Template:
        return self.template_spec.get_dart_template()

    @property
    def streamers(self) -> Sequence[Streamer]:
        """Sequence of Streamer objects, mirroring the TensorCore property."""
        return self.phs.streamers.streamers

    def transform_schedule(self, sched: Schedule) -> Schedule:
        """PHS does not rewrite the schedule before layout resolution."""
        return sched

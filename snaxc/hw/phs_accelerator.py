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
from snaxc.phs.decode import decode_abstract_graph
from snaxc.phs.encode import convert_generic_body_to_phs
from snaxc.phs.hw_conversion import get_switch_bitwidth
from snaxc.phs.template_spec import TemplateSpec


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

        self.phs = Phs.from_template(
            name=self.name,
            input_sizes=template_spec.get_input_sizes(),
            output_sizes=template_spec.get_output_sizes(),
            num_switches=true_switches,
            switch_bitwidths=switch_bitwidths,
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

        for operand, pattern, _streamer in zip(
            (*op.inputs, *op.outputs), op.stride_patterns.data, self.phs.streamers.streamers
        ):
            result.append(([], operand))
            for ts in pattern.temporal_strides:
                c = arith.ConstantOp.from_int_and_width(ts.data, 32)
                result.append(([c], c.result))
            for ub in pattern.upper_bounds:
                c = arith.ConstantOp.from_int_and_width(ub.data, 32)
                result.append(([c], c.result))
            for ss in pattern.spatial_strides:
                c = arith.ConstantOp.from_int_and_width(ss.data, 32)
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
        return self.template_spec.get_dart_template()

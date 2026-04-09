import string
from abc import ABC
from collections.abc import Sequence

from xdsl.dialects import arith, builtin
from xdsl.dialects.builtin import IntAttr, i32
from xdsl.ir import Operation, OpResult, SSAValue

from snaxc.dialects import snax_stream
from snaxc.dialects.dart import AccessPatternOp, StreamingRegionOpBase
from snaxc.dialects.snax_stream import StreamingRegionOp
from snaxc.hw.streamers.extensions.streamer_extension import StreamerExtension
from snaxc.hw.streamers.extensions.transpose_extension import (
    TransposeExtension,
)
from snaxc.hw.streamers.streamers import (
    HasAddressRemap,
    HasBroadcast,
    HasByteMask,
    HasChannelMask,
    Streamer,
    StreamerConfiguration,
    StreamerFlag,
    StreamerSystemType,
)
from snaxc.ir.dart.access_pattern import Template

c0_attr = builtin.IntegerAttr(0, builtin.IndexType())



class SNAXStreamer(ABC):
    """
    Abstract base class for SNAX Accelerators with Streamer interfaces.
    """

    streamer_config: StreamerConfiguration
    streamer_names: Sequence[str]
    streamer_setup_fields: Sequence[str]
    streamer_launch_fields: Sequence[str]

    zero_address = 0x1000_0040

    def __init__(self, streamer_config: StreamerConfiguration) -> None:
        self.streamer_config = streamer_config

        # set streamer names as a, b, c, d, ...
        self.streamer_names = list(string.ascii_lowercase[: self.streamer_config.size()])

        if self.streamer_config.system_type() == StreamerSystemType.Regular:
            self.streamer_setup_fields = self.get_streamer_setup_fields()
            self.streamer_launch_fields = self.get_streamer_launch_fields()
        else:
            self.streamer_setup_fields = self.get_xdma_streamer_setup_fields()
            self.streamer_launch_fields = self.get_xdma_streamer_launch_fields()

    def _generate_streamer_setup_vals(self, op: StreamingRegionOp) -> Sequence[tuple[Sequence[Operation], SSAValue]]:
        result: Sequence[tuple[Sequence[Operation], SSAValue]] = []

        do_broadcast = [False] * len(self.streamer_config.streamers)

        for operand, streamer in enumerate(self.streamer_config.streamers):
            # streamer must generate zero pattern if the stream is coming from c0
            is_zero_pattern = False
            if isinstance(opresult := op.operands[operand], OpResult):
                is_zero_pattern = isinstance(opresult.op, arith.ConstantOp) and opresult.op.value == c0_attr

            # base pointers (low, high)
            if is_zero_pattern:
                czero = arith.ConstantOp.from_int_and_width(self.zero_address, i32)
                result.append(([czero], czero.result))
            else:
                result.append(([], op.operands[operand]))
            result.append(([c0 := arith.ConstantOp.from_int_and_width(0, i32)], c0.result))

            # spatial strides
            for dim, flag in enumerate(streamer.spatial_dims):
                stride = op.stride_patterns.data[operand].spatial_strides.data[dim].data
                if stride == 0 and any(isinstance(opt, HasBroadcast) for opt in streamer.opts):
                    do_broadcast[operand] = True
                cst = arith.ConstantOp.from_int_and_width(stride, i32)
                result.append(([cst], cst.result))

            # loop bounds
            upper_bounds = op.stride_patterns.data[operand].upper_bounds.data
            # pad unused temporal bounds with 1's'
            upper_bounds = upper_bounds + ((IntAttr(1),) * (streamer.temporal_dim - len(upper_bounds)))

            # temporal strides
            temporal_strides = op.stride_patterns.data[operand].temporal_strides.data
            # pad unused spatial strides with 0's
            temporal_strides = temporal_strides + ((IntAttr(0),) * (streamer.temporal_dim - len(temporal_strides)))

            # ops for loop bounds
            for dim, flag in enumerate(streamer.temporal_dims):
                bound = upper_bounds[dim].data
                stride = temporal_strides[dim].data
                if flag == StreamerFlag.Reuse and bound > 1 and stride == 0:
                    # if internal reuse, bound can be set to 1
                    bound = 1
                cst = arith.ConstantOp.from_int_and_width(bound, i32)
                result.append(([cst], cst.result))

            # ops for temporal strides
            for dim, flag in enumerate(streamer.temporal_dims):
                stride = temporal_strides[dim].data
                if flag == StreamerFlag.Irrelevant:
                    # Irrelevant temporal strides should be zero
                    assert stride == 0
                cst = arith.ConstantOp.from_int_and_width(stride, i32)
                result.append(([cst], cst.result))

            # address remap:
            if any(isinstance(opt, HasAddressRemap) for opt in streamer.opts):
                c0 = arith.ConstantOp.from_int_and_width(0, i32)
                result.append(([c0], c0.result))

            # channel mask option
            if any(isinstance(opt, HasChannelMask) for opt in streamer.opts):
                if is_zero_pattern:
                    # mask all channels such that they generate zeros
                    c0 = arith.ConstantOp.from_int_and_width(0, i32)
                    result.append(([c0], c0.result))
                else:
                    # else, set to 32b111...111 (=-1) (all enabled)
                    n1 = arith.ConstantOp.from_int_and_width(-1, i32)
                    result.append(([n1], n1.result))

        # transpose specifications
        for operand, streamer in enumerate(self.streamer_config.streamers):
            if any(isinstance(opt, TransposeExtension) for opt in streamer.opts):
                # if we want to disable transpose, we need
                # a 1 to the transpose field, as it is an
                # extension bypass signal
                c0 = arith.ConstantOp.from_int_and_width(0, i32)
                result.append(([c0], c0.result))

        for operand, streamer in enumerate(self.streamer_config.streamers):
            if any(isinstance(opt, HasBroadcast) for opt in streamer.opts):
                if do_broadcast[operand]:
                    c1 = arith.ConstantOp.from_int_and_width(1, i32)
                    result.append(([c1], c1.result))
                else:
                    c0 = arith.ConstantOp.from_int_and_width(0, i32)
                    result.append(([c0], c0.result))

        return result

    def get_streamer_setup_fields(self) -> Sequence[str]:
        result: list[str] = []

        for name, streamer in zip(self.streamer_names, self.streamer_config.streamers):
            # base pointers
            result.extend([f"{name}_ptr_low", f"{name}_ptr_high"])
            # spatial strides
            result.extend([f"{name}_sstride_{i}" for i in range(streamer.spatial_dim)])
            # temporal bounds
            result.extend([f"{name}_bound_{i}" for i in range(streamer.temporal_dim)])
            # temporal strides
            result.extend([f"{name}_tstride_{i}" for i in range(streamer.temporal_dim)])
            # options
            if any(isinstance(opt, HasAddressRemap) for opt in streamer.opts):
                result.append(f"{name}_address_remap")
            if any(isinstance(opt, HasChannelMask) for opt in streamer.opts):
                result.append(f"{name}_channel_mask")

        # transpose specifications
        for streamer, name in zip(self.streamer_config.streamers, self.streamer_names):
            if any(isinstance(opt, TransposeExtension) for opt in streamer.opts):
                result.append(f"{name}_transpose")

        for streamer, name in zip(self.streamer_config.streamers, self.streamer_names):
            if any(isinstance(opt, HasBroadcast) for opt in streamer.opts):
                result.append(f"{name}_broadcast")

        return result

    def get_streamer_launch_fields(self) -> Sequence[str]:
        return ["launch_streamer"]

    def get_xdma_streamer_setup_fields(self) -> Sequence[str]:
        """
        Get the setup fields for the xDMA streamer.
        """
        result: list[str] = []

        assert self.streamer_config.system_type() == StreamerSystemType.DmaExt, (
            "This method should only be called for xDMA streamer configurations"
        )

        for name, streamer in zip(self.streamer_names, self.streamer_config.streamers):
            # base address
            result.extend([f"{name}_ptr_low", f"{name}_ptr_high"])

        for i, (name, streamer) in enumerate(zip(self.streamer_names, self.streamer_config.streamers)):
            # spatial strides
            result.extend([f"{name}_sstride_{i}" for i in range(streamer.spatial_dim)])
            # temporal bounds
            result.extend([f"{name}_bound_{i}" for i in range(streamer.temporal_dim)])
            # temporal strides
            result.extend([f"{name}_tstride_{i}" for i in range(streamer.temporal_dim)])
            # options
            result.extend([f"{name}_enabled_chan"])
            if any(isinstance(opt, HasByteMask) for opt in streamer.opts):
                result.append(f"{name}_enabled_byte")
            result.extend([f"{name}_bypass"])
            # Extensions
            for extension in streamer.opts:
                if isinstance(extension, StreamerExtension):
                    for i in range(extension.csr_length):
                        result.append(f"{name}_{extension.name}_{i}")

        return result

    def get_xdma_streamer_launch_fields(self) -> Sequence[str]:
        """
        Get the launch fields for the xDMA streamer.
        """
        return [
            "launch_start",
        ]

    def get_streamer_setup_dict(self, base_addr: int) -> tuple[int, dict[str, int]]:
        """
        Generate CSR Addresses for the setup of the streamers

        Parameters:
        base_addr (int): the base CSR address

        Returns:
        int: The next usable CSR address
        dict[str, int]: The dictionary mapping setup field to csr address
        """
        streamer_setup = {key: base_addr + i for i, key in enumerate(self.streamer_setup_fields)}
        base_addr += len(self.streamer_setup_fields)
        return base_addr, streamer_setup

    def get_streamer_launch_dict(self, base_addr: int) -> tuple[int, dict[str, int]]:
        """
        Generate CSR Addresses for the launch of the streamers

        Parameters:
        base_addr (int): the base CSR address

        Returns:
        int: The next usable CSR address
        dict[str, int]: The dictionary mapping setup field to csr address
        """
        streamer_launch = {key: base_addr + i for i, key in enumerate(self.streamer_launch_fields)}
        base_addr += len(self.streamer_launch_fields)

        # 1 busy register + 1 performance counter after launch field
        base_addr += 2

        return base_addr, streamer_launch

    @abstractmethod
    def get_template(self, op: StreamingRegionOpBase) -> Template:
        """
        Get the template for this acelerator to schedule a given
        stream.streaming_region operation.

        Returns template, template_bounds
        """
        raise NotImplementedError()

    def get_streamers(self, op: StreamingRegionOpBase) -> Sequence[Streamer]:
        """
        Return the set of streamers used for a given op.
        """
        return self.streamer_config.streamers

    def set_stride_patterns(
        self,
        op: AccessPatternOp,
        snax_stride_patterns: Sequence[snax_stream.StridePattern],
    ) -> tuple[
        Sequence[SSAValue],
        Sequence[SSAValue],
        Sequence[snax_stream.StridePattern],
        Sequence[Operation],
    ]:
        """
        Allows the accelerator to customize the found stride patterns
        after scheduling and layout resolution, for a given operation.

        Returns the new inputs, outputs and strides for the snax StridePattern
        operation, along with a list of ops to add to the IR.
        """
        return (op.inputs, op.outputs, snax_stride_patterns, [])



from abc import ABC
from collections.abc import Sequence

from xdsl.ir import SSAValue

from snaxc.dialects.dart import StreamingRegionOpBase
from snaxc.dialects.snax_stream import StridePattern
from snaxc.hw.streamers.streamers import Streamer, StreamerConfiguration
from snaxc.ir.dart.access_pattern import Template


class StreamerAccelerator(ABC):
    """
    Base class for accelerators with streamer interfaces.

    Provides the interface needed by the dart-to-snax-stream and
    related passes to compute stride patterns and layouts.
    """

    streamer_config: StreamerConfiguration

    def __init__(self, streamer_config: StreamerConfiguration) -> None:
        self.streamer_config = streamer_config

    def get_template(self, op: StreamingRegionOpBase) -> Template:
        """Return the dart Template for this accelerator's access pattern."""
        raise NotImplementedError()

    def get_streamers(self, op: StreamingRegionOpBase) -> Sequence[Streamer]:
        """Return the streamer configuration for a given operation."""
        return self.streamer_config.streamers

    def set_stride_patterns(
        self,
        op: StreamingRegionOpBase,
        snax_stride_patterns: Sequence[StridePattern],
    ) -> tuple[
        Sequence[SSAValue],
        Sequence[SSAValue],
        Sequence[StridePattern],
        list,
    ]:
        """
        Hook to customize stride patterns after scheduling and layout resolution.

        Returns (inputs, outputs, stride_patterns, ops_to_add).
        Default: pass through unchanged.
        """
        return (op.inputs, op.outputs, snax_stride_patterns, [])

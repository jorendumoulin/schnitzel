from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import prod


@dataclass
class Streamer:
    """
    A software representation of a single streamer.
    """

    access_width: int
    """The number of bytes of a single element access of this streamer"""

    temporal_dims: int
    spatial_dims: tuple[int, ...]
    name_base: str
    stream_type: str = "read"
    """One of "read", "write", or "readWrite". Determines the streamer's TCDM direction."""
    carry_used: bool = True
    """
    Only meaningful for ``readWrite``. When False, the BlackBox doesn't actually
    consume the carry-input data on this streamer; the Scala accelerator must
    still drive both sides for handshake/address pacing but should NOT gate
    other writers' writeData.valid on this streamer's readData.valid (otherwise
    the handshake deadlocks because the carry data never gets "consumed").
    """

    def addr_params(self) -> str:
        return f"{self.name_base}_addr"

    def ub_params(self) -> Iterable[str]:
        for i in range(self.temporal_dims):
            yield f"{self.name_base}_ub_{i}"

    def ts_params(self) -> Iterable[str]:
        for i in range(self.temporal_dims):
            yield f"{self.name_base}_ts_{i}"

    def ss_params(self) -> Iterable[str]:
        for i in range(self.spatial_dim):
            yield f"{self.name_base}_ss_{i}"

    @property
    def temporal_dim(self) -> int:
        """Number of temporal dimensions"""
        return self.temporal_dims

    @property
    def spatial_dim(self) -> int:
        """Number of spatial dimensions"""
        return len(self.spatial_dims)

    @property
    def spatial_width(self) -> int:
        """The number of ports this streamer has"""
        return prod(self.spatial_dims)

    @property
    def full_width(self) -> int:
        """The number of bytes accessed across all ports in a single cycle"""
        return self.access_width * prod(self.spatial_dims)

    @property
    def byte_offsets(self) -> Sequence[int]:
        """The spatial byte offset for contiguous access across all spatial dims"""
        return tuple(self.access_width * prod(self.spatial_dims[i + 1 :]) for i in range(self.spatial_dim))


@dataclass
class StreamerConfiguration:
    """
    A software representation of a set of streamers.
    """

    streamers: Sequence[Streamer]

    def size(self) -> int:
        return len(self.streamers)

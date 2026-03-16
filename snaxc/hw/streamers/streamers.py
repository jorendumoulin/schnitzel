from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass
from math import prod

from xdsl.utils.str_enum import StrEnum


class StreamerOpts(ABC):
    """
    Base class for streamer options.
    This class can be used to define custom options for streamers.
    """

    name: str


class HasAddressRemap(StreamerOpts):
    """
    Indicates that the streamer has an address remap.
    """

    name = "a"


class HasChannelMask(StreamerOpts):
    """
    Indicates that the streamer has a channel mask.
    """

    name = "c"


class HasByteMask(StreamerOpts):
    """
    Indicates that the streamer has a byte mask.
    """

    name = "bm"


class HasBroadcast(StreamerOpts):
    """
    Indicates that the streamer has a broadcast option.
    """

    name = "b"


class StreamerFlag(StrEnum):
    """
    Enum that specifies special flags for a streamer dimension.

    Attributes:
    -----------
    - Normal: 'n'
      Indicates that no special flags apply.
    - Irellevant : 'i'
      Indicates a dimension is irrelevant for this operand.
      In all cases, a zero should be set to the stride of this dimension.
      For spatial dims, the resulting value is assigned to a "virtual streamer"
      and will not be programmed.
    - Reuse : 'r'
      Only valid for temporal dims. Indicates that the values
      will be reused temporally and should only be fetched once.
      This results in the bound values being for this dimension fixed to 1.
    """

    Normal = "n"
    Irrelevant = "i"
    Reuse = "r"

    def __bool__(self) -> bool:
        """
        Overrides the default boolean conversion to ensure that the 'Normal'
        flag evaluates to False and all other flags evaluate to true
        """
        return self is not StreamerFlag.Normal


@dataclass
class Streamer:
    """
    A software representation of a single streamer
    """

    access_width: int
    """The number of bytes of a single element access of this streamer"""

    temporal_dims: int
    spatial_dims: tuple[int, ...]

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
    A software representation of a set of streamers
    """

    streamers: Sequence[Streamer]

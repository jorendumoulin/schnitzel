from snaxc.hw.streamers.streamers import (
    HasAddressRemap,
    HasBroadcast,
    HasByteMask,
    HasChannelMask,
)

from .streamer_extension import *
from .transpose_extension import TransposeExtension

STREAMER_OPT_MAP = {
    HasBroadcast().name: HasBroadcast,
    HasByteMask().name: HasByteMask,
    HasChannelMask().name: HasChannelMask,
    HasAddressRemap().name: HasAddressRemap,
    TransposeExtension().name: TransposeExtension,
}

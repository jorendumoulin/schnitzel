from dataclasses import dataclass

from snaxc.hw.accelerator import Accelerator
from snaxc.hw.streamers.streamers import (
    Streamer,
    StreamerConfiguration,
)


@dataclass
class Dma(Accelerator):
    """
    Accelerator interface class for the DMA.
    """

    name = "dma"
    streamers = StreamerConfiguration(
        [
            Streamer(64, 3, (1,)),
            Streamer(4, 3, (2, 2, 2)),
        ]
    )

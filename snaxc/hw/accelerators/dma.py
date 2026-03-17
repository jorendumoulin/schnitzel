from dataclasses import dataclass

from snaxc.hw.system import Accelerator
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
            Streamer(4, 3, (2, 2, 2, 2), "tcdm"),
            Streamer(64, 3, tuple(), "axi"),
        ]
    )

    def launch_param(self) -> str:
        return "start"

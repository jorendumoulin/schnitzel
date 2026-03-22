from dataclasses import dataclass

from snaxc.hw.streamers.streamers import Streamer, StreamerConfiguration
from snaxc.hw.system import Accelerator


@dataclass
class Alu(Accelerator):
    """
    Accelerator interface class for the ALU.
    """

    name = "alu"
    streamers = StreamerConfiguration(
        [
            Streamer(4, 3, (2, 2, 2), "in"),
            Streamer(4, 3, (2, 2, 2), "out"),
        ]
    )

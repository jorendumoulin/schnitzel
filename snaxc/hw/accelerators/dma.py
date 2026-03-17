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

    def param_values(self) -> dict[str, int]:
        base = 960
        csrs: list[str] = []
        for streamer in self.streamers.streamers:
            csrs.extend(streamer.ub_params())
            csrs.extend(streamer.ts_params())
            csrs.extend(streamer.ss_params())
        csrs.append(self.launch_param())
        return {param: base + idx for idx, param in enumerate(csrs)}

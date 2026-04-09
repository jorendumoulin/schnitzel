from dataclasses import dataclass

from snaxc.hw.streamers.streamers import (
    Streamer,
    StreamerConfiguration,
)
from snaxc.hw.system import Accelerator


@dataclass
class Dma(Accelerator):
    """
    Accelerator interface class for the DMA.
    """

    name = "dma"
    streamers = StreamerConfiguration(
        [
            Streamer(4, 4, (2, 2, 2, 2), "tcdm"),
            Streamer(64, 4, tuple(), "axi"),
        ]
    )

    def dir_param(self) -> str:
        return "dir"

    def launch_param(self) -> str:
        return "start"

    def param_values(self) -> dict[str, int]:
        base = 0x900
        csrs: list[str] = []
        for streamer in self.streamers.streamers:
            csrs.append(streamer.addr_params())
            csrs.extend(streamer.ts_params())
            csrs.extend(streamer.ub_params())
            csrs.extend(streamer.ss_params())
        csrs.append(self.dir_param())
        csrs.append(self.launch_param())
        return {param: base + idx for idx, param in enumerate(csrs)}

    def barrier_address(self) -> int:
        return self.param_values()[self.launch_param()]

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Self

from snaxc.hw.streamers.streamers import (
    Streamer,
)
from snaxc.hw.system import Accelerator


@dataclass
class Dma(Accelerator):
    """
    Accelerator interface class for the DMA.
    """

    name = "dma"
    tcdm: Streamer
    axi: Streamer

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> Self:
        tcdm = Streamer.from_params(params["tcdm"], "tcdm")
        axi = Streamer.from_params(params["axi"], "axi")
        return cls(tcdm, axi)

    @property
    def streamers(self) -> Sequence[Streamer]:
        return (self.tcdm, self.axi)

    def dir_param(self) -> str:
        return "dir"

    def launch_param(self) -> str:
        return "start"

    def param_values(self) -> dict[str, int]:
        base = 0x900
        csrs: list[str] = []
        for streamer in (self.tcdm, self.axi):
            csrs.append(streamer.addr_params())
            csrs.extend(streamer.ts_params())
            csrs.extend(streamer.ub_params())
            csrs.extend(streamer.ss_params())
        csrs.append(self.dir_param())
        csrs.append(self.launch_param())
        return {param: base + idx for idx, param in enumerate(csrs)}

    def barrier_address(self) -> int:
        return self.param_values()[self.launch_param()]

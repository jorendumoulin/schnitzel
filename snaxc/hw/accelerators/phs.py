from dataclasses import dataclass, field
from typing import Any

from snaxc.hw.streamers.streamers import Streamer, StreamerConfiguration
from snaxc.hw.system import Accelerator


@dataclass
class Phs(Accelerator):
    """
    Accelerator interface class for PHS-generated accelerators.

    The streamer configuration and switch parameters are derived
    at compile time from the PEOp and TemplateSpec, then passed
    to the schnitzel hardware generator via JSON config.
    """

    name: str = "phs"
    access_width: int = 4
    """Element access width in bytes (schnitzel default: 4 = 32-bit)"""

    num_switches: int = 0
    switch_bitwidths: list[int] = field(default_factory=lambda: list[int]())

    streamers: StreamerConfiguration = field(default_factory=lambda: StreamerConfiguration([]))

    @staticmethod
    def from_template(
        name: str,
        input_sizes: list[tuple[int, ...]],
        output_sizes: list[tuple[int, ...]],
        num_switches: int = 0,
        switch_bitwidths: list[int] | None = None,
        access_width: int = 4,
    ) -> "Phs":
        """
        Create a PHS accelerator from template input/output sizes.

        Parameters
        ----------
        name:
            Accelerator name (from PEOp sym_name).
        input_sizes:
            List of spatial dim tuples for each read streamer.
        output_sizes:
            List of spatial dim tuples for each write streamer.
        num_switches:
            Number of PHS switches (mux controls).
        switch_bitwidths:
            Bitwidth of each switch. Defaults to 32 for each.
        access_width:
            Element access width in bytes.
        """
        readers = [Streamer(access_width, len(dims), dims, f"in_{i}", "read") for i, dims in enumerate(input_sizes)]
        writers = [Streamer(access_width, len(dims), dims, f"out_{i}", "write") for i, dims in enumerate(output_sizes)]
        return Phs(
            name=name,
            access_width=access_width,
            num_switches=num_switches,
            switch_bitwidths=switch_bitwidths or [32] * num_switches,
            streamers=StreamerConfiguration([*readers, *writers]),
        )

    @staticmethod
    def from_config(config: dict[str, Any]) -> "Phs":
        """Create a Phs accelerator from a JSON config dict (as produced by PhsDriver)."""
        streamers: list[dict[str, Any]] = config.get("streamers", [])
        input_sizes: list[tuple[int, ...]] = [
            tuple(s["spatialDimSizes"]) for s in streamers if s["streamType"] == "read"
        ]
        output_sizes: list[tuple[int, ...]] = [
            tuple(s["spatialDimSizes"]) for s in streamers if s["streamType"] == "write"
        ]
        # moduleName from Scala is "{name}_array"; strip the suffix to get the
        # accelerator name that matches the PEOp sym_name.
        module_name = str(config.get("moduleName", "phs"))
        name = module_name.removesuffix("_array")
        return Phs.from_template(
            name=name,
            input_sizes=input_sizes,
            output_sizes=output_sizes,
            num_switches=int(config.get("numSwitches", 0)),
            switch_bitwidths=list(config.get("switchBitwidths", [])),
        )

    def param_values(self) -> dict[str, int]:
        """Compute CSR address map matching the Scala PhsAccelerator layout."""
        base = 0x900
        csrs: list[str] = []
        for streamer in self.streamers.streamers:
            csrs.append(streamer.addr_params())
            csrs.extend(streamer.ts_params())
            csrs.extend(streamer.ub_params())
            csrs.extend(streamer.ss_params())
        for i in range(self.num_switches):
            csrs.append(f"switch_{i}")
        csrs.append("start")
        return {param: base + idx for idx, param in enumerate(csrs)}

    def barrier_address(self) -> int:
        return self.param_values()["start"]

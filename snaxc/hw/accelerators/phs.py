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

        PE-array convention: every PE output is paired by position with a carry
        input at PE-input index ``len(input_sizes) - len(output_sizes) + k``.
        Each (carry, output) pair becomes a single ``readWrite`` streamer; any
        remaining inputs become ``read`` streamers. There are no pure ``write``
        streamers under this convention.

        Parameters
        ----------
        name:
            Accelerator name (from PEOp sym_name).
        input_sizes:
            Spatial dim tuples for every PE data-input port (pure reads
            followed by carries — the trailing ``len(output_sizes)`` entries
            are the carry side of readWrite pairs).
        output_sizes:
            Spatial dim tuples for every PE output port. ``len(output_sizes)``
            equals the number of readWrite pairs.
        num_switches:
            Number of PHS switches (mux controls).
        switch_bitwidths:
            Bitwidth of each switch. Defaults to 32 for each.
        access_width:
            Element access width in bytes.
        """
        num_outputs = len(output_sizes)
        num_pure_inputs = len(input_sizes) - num_outputs
        assert num_pure_inputs >= 0, (
            "Expect each PE output to be paired with a carry input — "
            f"got {len(input_sizes)} inputs and {num_outputs} outputs"
        )

        streamers: list[Streamer] = []
        for i in range(num_pure_inputs):
            dims = input_sizes[i]
            streamers.append(Streamer(access_width, len(dims), dims, f"in_{i}", "read"))
        for k in range(num_outputs):
            dims = output_sizes[k]
            streamers.append(Streamer(access_width, len(dims), dims, f"rw_{k}", "readWrite"))

        return Phs(
            name=name,
            access_width=access_width,
            num_switches=num_switches,
            switch_bitwidths=switch_bitwidths or [32] * num_switches,
            streamers=StreamerConfiguration(streamers),
        )

    @staticmethod
    def from_config(config: dict[str, Any]) -> "Phs":
        """Create a Phs accelerator from a JSON config dict (as produced by PhsDriver)."""
        streamers: list[dict[str, Any]] = config.get("streamers", [])
        # readWrite entries contribute one carry input AND one output; their
        # carry side comes after the pure reads in the PE-input list (matches
        # the encode-pass convention for derived input/output ordering).
        pure_read_sizes: list[tuple[int, ...]] = [
            tuple(s["spatialDimSizes"]) for s in streamers if s["streamType"] == "read"
        ]
        rw_sizes: list[tuple[int, ...]] = [
            tuple(s["spatialDimSizes"]) for s in streamers if s["streamType"] == "readWrite"
        ]
        write_sizes: list[tuple[int, ...]] = [
            tuple(s["spatialDimSizes"]) for s in streamers if s["streamType"] == "write"
        ]
        # Pure "write" entries appear in older configs; treat them as readWrite
        # so the structural pairing stays consistent.
        output_sizes: list[tuple[int, ...]] = [*rw_sizes, *write_sizes]
        input_sizes: list[tuple[int, ...]] = [*pure_read_sizes, *rw_sizes, *write_sizes]
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

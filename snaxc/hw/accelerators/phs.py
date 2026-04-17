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
        paired_outputs: tuple[int, ...] | None = None,
        carry_used: list[bool] | None = None,
    ) -> "Phs":
        """
        Create a PHS accelerator from template input/output sizes.

        PE-array convention: the trailing ``carry_no`` PE inputs are paired by
        position with the leading ``carry_no`` outputs as readWrite streamers.
        Inputs before that are pure ``read`` streamers; outputs after that are
        pure ``write`` streamers. ``carry_no`` defaults to ``len(output_sizes)``
        (every output paired) for back-compat.

        Parameters
        ----------
        name:
            Accelerator name (from PEOp sym_name).
        input_sizes:
            Spatial dim tuples for every PE data-input port (pure reads
            followed by carries — the trailing ``carry_no`` entries are the
            carry side of readWrite pairs).
        output_sizes:
            Spatial dim tuples for every PE output port.
        num_switches:
            Number of PHS switches (mux controls).
        switch_bitwidths:
            Bitwidth of each switch. Defaults to 32 for each.
        access_width:
            Element access width in bytes.
        paired_outputs:
            Indices of outputs that are paired with a carry-input. Default
            ``tuple(range(num_outputs))`` = every output paired, in order.
            The prune-unused-carries pass drops entries whose carry is dead.
        carry_used:
            Per-pair override for the Scala HW's ``carryUsed`` gating signal.
            Only meaningful for readWrite streamers. Length must match
            ``len(paired_outputs)``.
        """
        num_outputs = len(output_sizes)
        if paired_outputs is None:
            paired_outputs = tuple(range(num_outputs))
        assert all(0 <= k < num_outputs for k in paired_outputs), (
            f"paired_outputs {paired_outputs} out of range [0, {num_outputs})"
        )
        assert len(set(paired_outputs)) == len(paired_outputs), f"paired_outputs has duplicates: {paired_outputs}"
        carry_no = len(paired_outputs)
        num_pure_inputs = len(input_sizes) - carry_no
        assert num_pure_inputs >= 0, f"Need at least {carry_no} inputs to host carry-ins — got {len(input_sizes)}"
        if carry_used is None:
            carry_used = [True] * carry_no
        assert len(carry_used) == carry_no, f"carry_used has length {len(carry_used)} but carry_no={carry_no}"

        paired_set = set(paired_outputs)
        streamers: list[Streamer] = []
        for i in range(num_pure_inputs):
            dims = input_sizes[i]
            streamers.append(Streamer(access_width, len(dims), dims, f"in_{i}", "read"))
        for k, out_idx in enumerate(paired_outputs):
            dims = output_sizes[out_idx]
            streamers.append(
                Streamer(access_width, len(dims), dims, f"rw_{out_idx}", "readWrite", carry_used=carry_used[k])
            )
        for out_idx in range(num_outputs):
            if out_idx in paired_set:
                continue
            dims = output_sizes[out_idx]
            streamers.append(Streamer(access_width, len(dims), dims, f"out_{out_idx}", "write"))

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
        # Reconstruct the (pure_reads, readWrites, writes) layout `from_template`
        # expects. readWrite streamers contribute one output AND one carry-input;
        # paired_outputs records which output each readWrite binds.
        pure_read_sizes: list[tuple[int, ...]] = []
        rw_sizes: list[tuple[int, ...]] = []
        rw_carry_used: list[bool] = []
        write_sizes: list[tuple[int, ...]] = []
        for s in streamers:
            dims = tuple(s["spatialDimSizes"])
            t = s["streamType"]
            if t == "read":
                pure_read_sizes.append(dims)
            elif t == "readWrite":
                rw_sizes.append(dims)
                rw_carry_used.append(bool(s.get("carryUsed", True)))
            elif t == "write":
                write_sizes.append(dims)
            else:
                raise ValueError(f"Unknown streamType: {t}")
        # Paired outputs are listed first in the output list (by construction
        # matching from_template's ordering). pure "write" entries follow.
        output_sizes: list[tuple[int, ...]] = [*rw_sizes, *write_sizes]
        input_sizes: list[tuple[int, ...]] = [*pure_read_sizes, *rw_sizes]
        paired_outputs = tuple(range(len(rw_sizes)))
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
            paired_outputs=paired_outputs,
            carry_used=rw_carry_used,
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

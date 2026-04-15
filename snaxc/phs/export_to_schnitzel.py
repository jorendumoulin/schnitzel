"""
Export PHS accelerator configurations to schnitzel and call the PhsDriver
to generate SoC SystemVerilog.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence

from snaxc.hw.phs_accelerator import PhsAccelerator


def get_schnitzel_path() -> str:
    """Get the schnitzel project root directory from the tool location."""
    this_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(this_dir, "..", ".."))


def build_schnitzel_config(
    accelerators: Sequence[PhsAccelerator],
    sv_path: str,
) -> str:
    """
    Build a PhsAcceleratorConfig JSON string from registered accelerators.

    Returns a ``Seq[Seq[PhsAcceleratorConfig]]`` JSON string matching the
    schema expected by schnitzel's ``PhsDriver``.  All PHS accelerators are
    placed on core 1 (core 0 has DMA only).

    Parameters
    ----------
    accelerators:
        The PHS accelerators extracted from the MLIR module.
    sv_path:
        Path to the generated BlackBox SystemVerilog file, relative to the
        schnitzel project root.
    """
    configs: list[dict[str, object]] = []
    for acc in accelerators:
        phs = acc.phs

        # Streamer configs from the Phs accelerator.
        # Per-streamer mask: one bit per spatial dimension, min 1 bit.
        # Bit k enables spatial dim k. Read and write masks are tracked
        # separately so the blackbox can drive each streamer's spatialDimMask.
        streamer_cfgs: list[dict[str, str | int | list[int]]] = []
        write_mask_bitwidths: list[int] = []
        read_mask_bitwidths: list[int] = []
        for streamer in phs.streamers.streamers:
            is_writer = streamer.name_base.startswith("out_")
            streamer_cfgs.append(
                {
                    "streamType": "write" if is_writer else "read",
                    "nTemporalDims": streamer.temporal_dims,
                    "spatialDimSizes": list(streamer.spatial_dims),
                }
            )
            width = max(1, len(streamer.spatial_dims))
            if is_writer:
                write_mask_bitwidths.append(width)
            else:
                read_mask_bitwidths.append(width)

        # Module name: PEOp sym_name + "_array" (matches firtool output convention)
        module_name = acc.name + "_array"

        configs.append(
            {
                "streamers": streamer_cfgs,
                "numSwitches": phs.num_switches,
                "switchBitwidths": phs.switch_bitwidths,
                "maskBitwidths": write_mask_bitwidths,
                "readMaskBitwidths": read_mask_bitwidths,
                "moduleName": module_name,
                "svPath": sv_path,
            }
        )

    # Seq[Seq[PhsAcceleratorConfig]]: core 0 = empty, core 1 = all PHS accels
    return json.dumps([[], configs])


def call_phs_driver(
    accelerators: Sequence[PhsAccelerator],
    output_hardware: str,
    output_dir: str,
) -> dict[str, object]:
    """
    Call the schnitzel PhsDriver via mill to generate SoC verilog.

    Returns the system config JSON (as a dict) produced by the hardware generator.

    Parameters
    ----------
    accelerators:
        The PHS accelerators extracted from the MLIR module.
    output_hardware:
        Path to the generated BlackBox SystemVerilog file (as written by phsc).
    output_dir:
        Directory where the SoC SystemVerilog should be generated.
    """
    schnitzel_path = get_schnitzel_path()

    # Compute sv_path relative to schnitzel root
    sv_path = os.path.relpath(os.path.abspath(output_hardware), schnitzel_path)

    config_json = build_schnitzel_config(accelerators, sv_path)
    abs_output_dir = os.path.abspath(output_dir)

    mill_cmd = [
        "./mill",
        "schnitzel.runMain",
        "phs.PhsDriver",
        f"--phs-config={config_json}",
        f"--output-dir={abs_output_dir}",
    ]
    print(f"Calling PhsDriver: output-dir={abs_output_dir}")
    try:
        subprocess.run(
            mill_cmd,
            cwd=schnitzel_path,
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error during schnitzel hardware generation:\n{e}", file=sys.stderr)
        raise SystemExit(e.returncode or 1)

    # Read the system config produced by PhsDriver
    config_path = os.path.join(abs_output_dir, "config.json")
    with open(config_path) as f:
        return json.load(f)

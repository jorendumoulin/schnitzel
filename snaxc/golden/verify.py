"""End-to-end golden-vs-device verification harness.

Lowers `--spec` MLIR to a host .so, computes expected outputs from `--inputs`,
then runs `--elf` on the verilator sim (via the simulator pybind module),
injects inputs by ELF symbol name, reads outputs, compares.

Integer outputs: bit-exact (pipeline fails on mismatch).
Float outputs: bit-exact (logged, not gating) + tolerance (gating).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from sim.sim import Simulator
from snaxc.golden.golden_runner import TensorSpec, run_golden
from snaxc.golden.lower_to_host import compile_spec_to_so

_NP_DTYPES = {
    "int8": np.int8,
    "int16": np.int16,
    "int32": np.int32,
    "int64": np.int64,
    "uint8": np.uint8,
    "uint16": np.uint16,
    "uint32": np.uint32,
    "uint64": np.uint64,
    "float32": np.float32,
    "float64": np.float64,
}


@dataclass
class InputSpec:
    name: str
    array: np.ndarray


def _materialize_input(name: str, blob: dict[str, Any]) -> InputSpec:
    dtype = np.dtype(_NP_DTYPES[blob["dtype"]])
    shape: tuple[int, ...] = tuple(int(s) for s in blob["shape"])
    if "values" in blob:
        arr = np.array(blob["values"], dtype=dtype).reshape(shape)
    elif "seed" in blob:
        rng = np.random.default_rng(int(blob["seed"]))
        lo, hi = blob.get("range", [0, 100])
        if np.issubdtype(dtype, np.integer):
            arr = rng.integers(int(lo), int(hi), size=shape, dtype=dtype)
        else:
            arr = rng.uniform(float(lo), float(hi), size=shape).astype(dtype)
    else:
        raise ValueError(f"Input {name} needs 'values' or 'seed'")
    return InputSpec(name=name, array=arr)


def _compare(actual: np.ndarray, expected: np.ndarray, name: str, rtol: float, atol: float) -> bool:
    if np.issubdtype(actual.dtype, np.integer):
        ok = np.array_equal(actual, expected)
        if not ok:
            mism = np.flatnonzero(actual.ravel() != expected.ravel())
            print(f"FAIL {name}: {len(mism)}/{actual.size} mismatches", file=sys.stderr)
            for i in mism[:16]:
                print(f"  [{i}] actual={actual.ravel()[i]} expected={expected.ravel()[i]}", file=sys.stderr)
        return ok

    # Float path: dual check.
    a_u = actual.view(np.dtype(f"uint{actual.dtype.itemsize * 8}"))
    e_u = expected.view(np.dtype(f"uint{expected.dtype.itemsize * 8}"))
    bit_exact = np.array_equal(a_u, e_u)
    if bit_exact:
        print(f"  {name}: bit-exact OK")
    else:
        diff = np.abs(a_u.astype(np.int64) - e_u.astype(np.int64))
        print(
            f"  WARN {name}: not bit-exact, max ulp delta={int(diff.max())} "
            f"({int((diff != 0).sum())}/{actual.size} elements differ)"
        )
    tol_ok = np.allclose(actual, expected, rtol=rtol, atol=atol, equal_nan=True)
    if not tol_ok:
        worst = np.argmax(np.abs(actual.ravel() - expected.ravel()))
        print(
            f"FAIL {name}: tolerance violated (rtol={rtol}, atol={atol}), "
            f"worst idx={worst} actual={actual.ravel()[worst]} expected={expected.ravel()[worst]}",
            file=sys.stderr,
        )
    return tol_ok


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--elf", required=True, type=Path)
    p.add_argument("--spec", required=True, type=Path, help="test_software.mlir")
    p.add_argument("--inputs", required=True, type=Path, help="inputs.json")
    p.add_argument("--build-dir", required=True, type=Path)
    p.add_argument("--sim-lib", required=True, type=Path, help="path to my_module.cpython-*.so for this kernel")
    p.add_argument(
        "--vlt-args", default="", help="space-separated Verilator runtime args / plusargs (e.g. '+verbose=1 +trace')"
    )
    args = p.parse_args()

    cfg = json.loads(args.inputs.read_text())
    fn = cfg["fn"]
    inputs = [_materialize_input(name, blob) for name, blob in cfg["inputs"].items()]
    out_specs = [
        TensorSpec(
            name=o["name"],
            dtype=np.dtype(_NP_DTYPES[o["dtype"]]),
            shape=tuple(o["shape"]),
        )
        for o in cfg["outputs"]
    ]
    rtol = float(cfg.get("rtol", 1e-5))
    atol = float(cfg.get("atol", 1e-6))

    print(f"[verify] lowering {args.spec} -> .so")
    so = compile_spec_to_so(args.spec, args.build_dir)

    print(f"[verify] computing golden via {so}")
    expected = run_golden(so, fn, [i.array for i in inputs], out_specs)

    print(f"[verify] launching sim on {args.elf}")
    sim = Simulator(elf_paths=[str(args.elf)], lib_path=args.sim_lib, vlt_args=args.vlt_args)
    syms = sim.get_symbols()
    for inp in inputs:
        if inp.name not in syms:
            print(f"FAIL: input symbol '{inp.name}' not in ELF", file=sys.stderr)
            return 2
        sim.write_data(syms[inp.name], inp.array.tobytes())
    # Zero-init outputs in device memory so the device sees the same initial
    # accumulator state as the golden (run_golden allocates zero-filled outputs).
    for spec in out_specs:
        if spec.name in syms:
            nbytes = int(np.prod(spec.shape)) * spec.dtype.itemsize
            sim.write_data(syms[spec.name], bytes(nbytes))

    rc = sim.run()
    print(f"[verify] sim exited with rc={rc}")
    if rc != 0:
        print("FAIL: sim returned non-zero", file=sys.stderr)
        return 2

    all_ok = True
    for spec, exp in zip(out_specs, expected):
        if spec.name not in syms:
            print(f"FAIL: output symbol '{spec.name}' not in ELF", file=sys.stderr)
            return 2
        nbytes = int(np.prod(spec.shape)) * spec.dtype.itemsize
        raw = sim.read_data(syms[spec.name], nbytes)
        actual = np.frombuffer(raw, dtype=spec.dtype).reshape(spec.shape).copy()
        if not _compare(actual, exp, spec.name, rtol, atol):
            all_ok = False

    if all_ok:
        print("[verify] TEST PASSED")
        return 0
    print("[verify] TEST FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())

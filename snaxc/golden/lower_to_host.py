"""Lower a spec MLIR file (e.g. test_software.mlir) to a host-executable .so.

Pipeline: optional bufferization -> postproc (linalg -> llvm) -> mlir-translate -> clang.
Output: a shared library exposing `_mlir_ciface_<fn_name>` for each public func.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

# Matches the postproc pipeline used for device codegen, retargeted at 64-bit host.
POSTPROC_FLAGS_HOST: tuple[str, ...] = (
    "--convert-linalg-to-loops",
    "--convert-scf-to-cf",
    "--lower-affine",
    "--canonicalize",
    "--cse",
    "--convert-math-to-llvm",
    "--llvm-request-c-wrappers",
    "--expand-strided-metadata",
    "--lower-affine",
    "--convert-index-to-llvm=index-bitwidth=64",
    "--convert-cf-to-llvm=index-bitwidth=64",
    "--convert-arith-to-llvm=index-bitwidth=64",
    "--convert-func-to-llvm=index-bitwidth=64",
    "--finalize-memref-to-llvm=index-bitwidth=64",
    "--canonicalize",
    "--reconcile-unrealized-casts",
)

BUFFERIZE_FLAGS: tuple[str, ...] = (
    "--empty-tensor-to-alloc-tensor",
    "--one-shot-bufferize=bufferize-function-boundaries=1",
    "--canonicalize",
)


def _needs_bufferize(mlir_text: str) -> bool:
    return bool(re.search(r"\btensor<", mlir_text))


def compile_spec_to_so(spec_mlir: Path, build_dir: Path, mlir_opt: str = "mlir-opt",
                       mlir_translate: str = "mlir-translate", clang: str = "clang") -> Path:
    spec_mlir = Path(spec_mlir).resolve()
    build_dir = Path(build_dir).resolve()
    build_dir.mkdir(parents=True, exist_ok=True)

    text = spec_mlir.read_text()
    flags: list[str] = []
    if _needs_bufferize(text):
        flags.extend(BUFFERIZE_FLAGS)
    flags.extend(POSTPROC_FLAGS_HOST)

    lowered = build_dir / "golden.lowered.mlir"
    subprocess.run(
        [mlir_opt, str(spec_mlir), *flags, "-o", str(lowered)],
        check=True,
    )

    ll = build_dir / "golden.ll"
    subprocess.run(
        [mlir_translate, "--mlir-to-llvmir", str(lowered), "-o", str(ll)],
        check=True,
    )

    so = build_dir / "golden.so"
    subprocess.run(
        [clang, "-O2", "-shared", "-fPIC", str(ll), "-o", str(so)],
        check=True,
    )
    return so

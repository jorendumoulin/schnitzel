"""Call an MLIR-lowered kernel from Python with numpy I/O.

The lowered .so exposes `_mlir_ciface_<fn>` taking pointer(s) to MemRef descriptors.
For functions where MLIR returns by value, the C-interface keeps the return in the
last memref-pointer argument (when bufferized with function-boundary buffer-out-args)
or via a struct return. Here we only handle the out-param convention (current spec
form: memref ins + memref out param, no return).
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class TensorSpec:
    name: str
    dtype: np.dtype
    shape: tuple[int, ...]


def _memref_struct(rank: int) -> type[ctypes.Structure]:
    class MemRef(ctypes.Structure):
        _fields_ = [
            ("allocated", ctypes.c_void_p),
            ("aligned", ctypes.c_void_p),
            ("offset", ctypes.c_int64),
            ("sizes", ctypes.c_int64 * max(rank, 1)),
            ("strides", ctypes.c_int64 * max(rank, 1)),
        ]
    MemRef.__name__ = f"MemRef{rank}D"
    return MemRef


def _make_descriptor(arr: np.ndarray) -> ctypes.Structure:
    rank = arr.ndim
    MemRef = _memref_struct(rank)
    desc = MemRef()
    ptr = arr.ctypes.data
    desc.allocated = ptr
    desc.aligned = ptr
    desc.offset = 0
    sizes = (ctypes.c_int64 * max(rank, 1))(*arr.shape) if rank > 0 else (ctypes.c_int64 * 1)(0)
    elem_size = arr.dtype.itemsize
    strides_elems = tuple(s // elem_size for s in arr.strides) if rank > 0 else (1,)
    strides = (ctypes.c_int64 * max(rank, 1))(*strides_elems)
    desc.sizes = sizes
    desc.strides = strides
    return desc


def run_golden(so_path: Path, fn_name: str, inputs: list[np.ndarray],
               outputs: list[TensorSpec]) -> list[np.ndarray]:
    """Invoke `_mlir_ciface_<fn_name>(in0, in1, ..., out0, out1, ...)`.

    All inputs and output buffers are passed as MemRef descriptor pointers.
    Out arrays are allocated zero-filled per the provided TensorSpec list.
    Returns the populated output arrays.
    """
    lib = ctypes.CDLL(str(so_path))
    func = getattr(lib, f"_mlir_ciface_{fn_name}")
    func.restype = None
    n_args = len(inputs) + len(outputs)
    func.argtypes = [ctypes.c_void_p] * n_args

    in_arrs = [np.ascontiguousarray(a) for a in inputs]
    out_arrs = [np.zeros(spec.shape, dtype=spec.dtype) for spec in outputs]
    descs = [_make_descriptor(a) for a in in_arrs + out_arrs]
    # Keep references alive for the duration of the call.
    arg_ptrs = [ctypes.cast(ctypes.pointer(d), ctypes.c_void_p) for d in descs]
    func(*arg_ptrs)
    return out_arrs

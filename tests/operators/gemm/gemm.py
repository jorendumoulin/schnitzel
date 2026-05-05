import os
from io import StringIO
from typing import Sequence

import numpy as np
from xdsl.builder import Builder
from xdsl.dialects.arith import ConstantOp
from xdsl.dialects.builtin import (
    DenseIntOrFPElementsAttr,
    ModuleOp,
    StringAttr,
    TensorType,
    i8,
    i32,
)
from xdsl.dialects.func import FuncOp, ReturnOp
from xdsl.dialects.linalg import AddOp, QuantizedMatmulOp
from xdsl.dialects.memref import GlobalOp
from xdsl.dialects.tensor import EmptyOp
from xdsl.dialects.arith import ConstantOp
from xdsl.ir import BlockArgument
from xdsl.parser import NoneAttr
from xdsl.printer import Printer


def gemm(m: int = 16, n: int = 16, k: int = 16):

    # Define Variables For Program:
    a_type = TensorType(i8, (m, k))
    b_type = TensorType(i8, (k, n))
    output_type = TensorType(i32, (m, n))

    # Define Program:
    @Builder.implicit_region([a_type, b_type])
    def func_body(args: Sequence[BlockArgument]) -> None:
        c0 = ConstantOp.from_int_and_width(0, 32)
        empty_tensor = EmptyOp([], output_type)
        result = QuantizedMatmulOp([args[0], args[1], c0.result, c0.result], empty_tensor.results)
        ReturnOp(result)

    function = FuncOp.from_region("gemm", [a_type, b_type], [output_type], func_body)

    return ModuleOp([function])


if __name__ == "__main__":
    # Get the name of the current Python script and replace its extension with .mlir
    script_name = os.path.basename(__file__)
    mlir_filename = os.path.splitext(script_name)[0] + ".mlir"

    # Generate IR and write it to the specified MLIR file
    with open(mlir_filename, "w") as output_file:
        output_file.write(str(gemm()))

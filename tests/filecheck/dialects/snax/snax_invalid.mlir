// RUN: XDSL_VERIFY_DIAG

"builtin.module"() ({
  %0 = arith.constant 45 : index
  %1 = "snax.alloc"(%0) <{"memory_space" = 1 : i32, "alignment" = 64 : i32}> : (index) -> !llvm.struct<(i32)>
}) : () -> ()

// CHECK: Operation does not verify: Invalid Memref Descriptor: Expected descriptor to have 3 (0-D) or 5 (ranked) fields

// -----

"builtin.module"() ({
  %0 = arith.constant 45 : index
  %1 = "snax.alloc"(%0) <{"memory_space" = 2 : i32, "alignment" = 64 : i32}> : (index) -> !llvm.struct<(!llvm.ptr, !llvm.ptr, !llvm.array<2 x i32>, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
}) : () -> ()

// CHECK: Operation does not verify: Invalid Memref Descriptor: Expected third element to be IntegerType

// -----

"builtin.module"() ({
  %0 = arith.constant 45 : index
  %1 = "snax.alloc"(%0) <{"memory_space" = 2 : i32, "alignment" = 64 : i32}> : (index) -> !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<1 x i32>, !llvm.array<2 x i32>)>
}) : () -> ()

// CHECK: Operation does not verify: Invalid Memref Descriptor: Expected shape and strides to have the same dimension

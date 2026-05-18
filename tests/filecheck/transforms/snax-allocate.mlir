// RUN: snax-opt --split-input-file %s -p snax-allocate | filecheck %s

"builtin.module"() ({
  %0 = "test.op"() : () -> (index)
  %1 = "snax.alloc"(%0, %0, %0) <{"memory_space" = "L1", "alignment" = 64 : i32}> : (index, index, index) -> !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
}) : () -> ()

// CHECK:      builtin.module {
// CHECK-NEXT:   %0 = "test.op"() : () -> index
// CHECK-NEXT:   %1 = arith.constant 64 : index
// CHECK-NEXT:   %2 = func.call @snax_alloc_l1(%0, %1) : (index, index) -> !llvm.ptr
// CHECK-NEXT:   %3 = llvm.load %2 : !llvm.ptr -> !llvm.struct<(!llvm.ptr, !llvm.ptr)>
// CHECK-NEXT:   %4 = llvm.extractvalue %3[0] : !llvm.struct<(!llvm.ptr, !llvm.ptr)>
// CHECK-NEXT:   %5 = llvm.extractvalue %3[1] : !llvm.struct<(!llvm.ptr, !llvm.ptr)>
// CHECK-NEXT:   %6 = llvm.mlir.undef : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
// CHECK-NEXT:   %7 = llvm.insertvalue %4, %6[0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %8 = llvm.insertvalue %5, %7[1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %9 = arith.constant 0 : i32
// CHECK-NEXT:   %10 = llvm.insertvalue %9, %8[2] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %11 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:   %12 = llvm.insertvalue %11, %10[3, 0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %13 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:   %14 = llvm.insertvalue %13, %12[3, 1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   func.func private @snax_alloc_l1(index, index) -> !llvm.ptr
// CHECK-NEXT: }

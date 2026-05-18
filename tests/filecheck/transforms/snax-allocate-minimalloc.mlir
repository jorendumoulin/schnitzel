// RUN: snax-opt --split-input-file --system-config %S/../test_system_config.json %s -p snax-allocate{mode=minimalloc} | filecheck %s

builtin.module {
  func.func public @test() {
    %0 = arith.constant 5 : index
    %1 = arith.constant 13 : index
    %2 = "snax.alloc"(%1, %0, %0) <{memory_space = "Test", alignment = 10 : i32}> : (index, index, index) -> !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
    %3 = "builtin.unrealized_conversion_cast" (%2) : (!llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>) ->  memref<5x5xi32>
    %4 = "snax.alloc"(%1, %0, %0) <{memory_space = "Test", alignment = 10 : i32}> : (index, index, index) -> !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
    %5 = "builtin.unrealized_conversion_cast" (%4) : (!llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>) -> memref<5x5xi32>
    "test.op"(%3) : (memref<5x5xi32>) -> ()
    "test.op"(%5) : (memref<5x5xi32>) -> ()
    %6 = "snax.alloc"(%1, %0, %0) <{memory_space = "Test", alignment = 14 : i32}> : (index, index, index) -> !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
    %7 = "builtin.unrealized_conversion_cast" (%6) : (!llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>) -> memref<5x5xi32>
    "test.op"(%7) : (memref<5x5xi32>) -> ()
    func.return
  }
}

// CHECK:      builtin.module {
// CHECK-NEXT:   func.func public @test() {
// CHECK-NEXT:     %0 = arith.constant 5 : index
// CHECK-NEXT:     %1 = arith.constant 13 : index
//                    First allocation at 0:
// CHECK-NEXT:     %2 = arith.constant 0 : i32
// CHECK-NEXT:     %3 = llvm.inttoptr %2 : i32 to !llvm.ptr
// CHECK-NEXT:     %4 = llvm.mlir.undef : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
// CHECK-NEXT:     %5 = llvm.insertvalue %3, %4[0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %6 = llvm.insertvalue %3, %5[1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %7 = arith.constant 0 : i32
// CHECK-NEXT:     %8 = llvm.insertvalue %7, %6[2] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %9 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:     %10 = llvm.insertvalue %9, %8[3, 0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %11 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:     %12 = llvm.insertvalue %11, %10[3, 1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %13 = builtin.unrealized_conversion_cast %12 : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)> to memref<5x5xi32>
//
//                    Second allocation at 20:
// CHECK-NEXT:     %14 = arith.constant 20 : i32
// CHECK-NEXT:     %15 = llvm.inttoptr %14 : i32 to !llvm.ptr
// CHECK-NEXT:     %16 = llvm.mlir.undef : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
// CHECK-NEXT:     %17 = llvm.insertvalue %15, %16[0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %18 = llvm.insertvalue %15, %17[1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %19 = arith.constant 0 : i32
// CHECK-NEXT:     %20 = llvm.insertvalue %19, %18[2] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %21 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:     %22 = llvm.insertvalue %21, %20[3, 0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %23 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:     %24 = llvm.insertvalue %23, %22[3, 1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %25 = builtin.unrealized_conversion_cast %24 : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)> to memref<5x5xi32>
// CHECK-NEXT:     "test.op"(%13) : (memref<5x5xi32>) -> ()
// CHECK-NEXT:     memref.dealloc %13 : memref<5x5xi32>
// CHECK-NEXT:     "test.op"(%25) : (memref<5x5xi32>) -> ()
// CHECK-NEXT:     memref.dealloc %25 : memref<5x5xi32>
//
//                    Third allocation back at 0:
// CHECK-NEXT:     %26 = arith.constant 0 : i32
// CHECK-NEXT:     %27 = llvm.inttoptr %26 : i32 to !llvm.ptr
// CHECK-NEXT:     %28 = llvm.mlir.undef : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
// CHECK-NEXT:     %29 = llvm.insertvalue %27, %28[0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %30 = llvm.insertvalue %27, %29[1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %31 = arith.constant 0 : i32
// CHECK-NEXT:     %32 = llvm.insertvalue %31, %30[2] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %33 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:     %34 = llvm.insertvalue %33, %32[3, 0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %35 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:     %36 = llvm.insertvalue %35, %34[3, 1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:     %37 = builtin.unrealized_conversion_cast %36 : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)> to memref<5x5xi32>
// CHECK-NEXT:     "test.op"(%37) : (memref<5x5xi32>) -> ()
// CHECK-NEXT:     memref.dealloc %37 : memref<5x5xi32>
// CHECK-NEXT:     func.return
// CHECK-NEXT:   }
// CHECK-NEXT: }

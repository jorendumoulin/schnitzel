// RUN: snax-opt --split-input-file --system-config %S/../test_system_config.json %s -p snax-allocate{mode=static} | filecheck %s

"builtin.module"() ({
  %0 = arith.constant 5 : index
  %1 = arith.constant 13 : index
  %2 = "snax.alloc"(%1, %0, %0) <{"memory_space" = "Test", "alignment" = 10 : i32}> : (index, index, index) -> !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
  %3 = "snax.alloc"(%1, %0, %0) <{"memory_space" = "Test", "alignment" = 10 : i32}> : (index, index, index) -> !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
  %4 = "snax.alloc"(%1, %0, %0) <{"memory_space" = "Test", "alignment" = 14 : i32}> : (index, index, index) -> !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
}) : () -> ()

// CHECK:      builtin.module {
// CHECK-NEXT:   %0 = arith.constant 5 : index
// CHECK-NEXT:   %1 = arith.constant 13 : index

//                    First allocation at 0:
// CHECK-NEXT:   %2 = arith.constant 0 : i32
// CHECK-NEXT:   %3 = llvm.inttoptr %2 : i32 to !llvm.ptr
// CHECK-NEXT:   %4 = llvm.mlir.undef : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
// CHECK-NEXT:   %5 = llvm.insertvalue %3, %4[0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %6 = llvm.insertvalue %3, %5[1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %7 = arith.constant 0 : i32
// CHECK-NEXT:   %8 = llvm.insertvalue %7, %6[2] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %9 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:   %10 = llvm.insertvalue %9, %8[3, 0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %11 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:   %12 = llvm.insertvalue %11, %10[3, 1] : !llvm.struct<(!llvm.ptr
//
//                     Second allocation at 20:
// CHECK-NEXT:   %13 = arith.constant 20 : i32
// CHECK-NEXT:   %14 = llvm.inttoptr %13 : i32 to !llvm.ptr
// CHECK-NEXT:   %15 = llvm.mlir.undef : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
// CHECK-NEXT:   %16 = llvm.insertvalue %14, %15[0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %17 = llvm.insertvalue %14, %16[1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %18 = arith.constant 0 : i32
// CHECK-NEXT:   %19 = llvm.insertvalue %18, %17[2] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %20 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:   %21 = llvm.insertvalue %20, %19[3, 0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %22 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:   %23 = llvm.insertvalue %22, %21[3, 1] : !llvm.struct<(!llvm.ptr
//
//                     Third allocation at 42:
// CHECK-NEXT:   %24 = arith.constant 42 : i32
// CHECK-NEXT:   %25 = llvm.inttoptr %24 : i32 to !llvm.ptr
// CHECK-NEXT:   %26 = llvm.mlir.undef : !llvm.struct<(!llvm.ptr, !llvm.ptr, i32, !llvm.array<2 x i32>, !llvm.array<2 x i32>)>
// CHECK-NEXT:   %27 = llvm.insertvalue %25, %26[0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %28 = llvm.insertvalue %25, %27[1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %29 = arith.constant 0 : i32
// CHECK-NEXT:   %30 = llvm.insertvalue %29, %28[2] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %31 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:   %32 = llvm.insertvalue %31, %30[3, 0] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT:   %33 = builtin.unrealized_conversion_cast %0 : index to i32
// CHECK-NEXT:   %34 = llvm.insertvalue %33, %32[3, 1] : !llvm.struct<(!llvm.ptr
// CHECK-NEXT: }

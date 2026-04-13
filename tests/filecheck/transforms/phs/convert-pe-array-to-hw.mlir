// RUN: snax-opt %s -p convert-pe-to-hw | filecheck %s

// Test that convert-pe-to-hw converts PEArrayOp with body to hw.module

phs.pe @myacc with %0 (%1 : i32, %2 : i32) {
  %3 = phs.choose @_0 with %0 (%1 : i32, %2 : i32) -> i32
    0) (%4, %5) {
      %6 = arith.muli %4, %5 : i32
      phs.yield %6 : i32
    }
    1) (%7, %8) {
      %9 = arith.addi %7, %8 : i32
      phs.yield %9 : i32
    }
  phs.yield %3 : i32
}

phs.pe_array @myacc_array(%0 : !hw.array<4xi32>, %1 : !hw.array<4xi32>, %2 : index) -> (!hw.array<4xi32>) {
  %3 = arith.constant 0 : i2
  %4 = hw.array_get %0[%3] : !hw.array<4xi32>, i2
  %5 = arith.constant 0 : i2
  %6 = hw.array_get %1[%5] : !hw.array<4xi32>, i2
  %7 = phs.instance "myacc_pe_0" @myacc(%4, %6 : i32, i32) switches(%2 : index) -> i32
  %8 = arith.constant 1 : i2
  %9 = hw.array_get %0[%8] : !hw.array<4xi32>, i2
  %10 = arith.constant 1 : i2
  %11 = hw.array_get %1[%10] : !hw.array<4xi32>, i2
  %12 = phs.instance "myacc_pe_1" @myacc(%9, %11 : i32, i32) switches(%2 : index) -> i32
  %13 = hw.array_create %12, %7 : i32
  phs.yield %13 : !hw.array<2xi32>
}

// The single PE module
// CHECK: hw.module private @myacc(in %0 data_0: i32, in %1 data_1: i32, in %2 switch_0: i1, out out_0: i32) {
// CHECK:   hw.output

// The PE array module with hw.instance ops
// CHECK: hw.module @myacc_array(in %0 in_0: !hw.array<4xi32>, in %1 in_1: !hw.array<4xi32>, in %2 in_2: i1, out out_0: !hw.array<2xi32>) {
// CHECK:   hw.instance "myacc_pe_0" @myacc
// CHECK:   hw.instance "myacc_pe_1" @myacc
// CHECK:   hw.array_create
// CHECK:   hw.output
// CHECK: }

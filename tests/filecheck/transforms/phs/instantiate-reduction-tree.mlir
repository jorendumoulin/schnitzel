// RUN: snax-opt %s -p convert-pe-to-hw | filecheck %s

// Test reduction tree wiring: 3 PEs in a binary tree for 4 inputs.
// PE[0] and PE[1] read pairs from the input array (leaf stage).
// PE[2] combines their outputs (root stage).

phs.pe @acc1 with %0 (%1 : i32, %2 : i32) {
  %3 = phs.choose @_0 with %0 (%1 : i32, %2 : i32) -> i32
    0) (%4, %5) {
      %6 = arith.addi %4, %5 : i32
      phs.yield %6 : i32
    }
    1) (%7, %8) {
      %9 = arith.muli %7, %8 : i32
      phs.yield %9 : i32
    }
  phs.yield %3 : i32
}

phs.pe_array @acc1_array(%0 : !hw.array<4xi32>, %1 : index) -> (i32) {
  %2 = arith.constant 0 : i2
  %3 = hw.array_get %0[%2] : !hw.array<4xi32>, i2
  %4 = arith.constant 1 : i2
  %5 = hw.array_get %0[%4] : !hw.array<4xi32>, i2
  %6 = phs.instance "acc1_pe_0" @acc1(%3, %5 : i32, i32) switches(%1 : index) -> i32
  %7 = arith.constant -2 : i2
  %8 = hw.array_get %0[%7] : !hw.array<4xi32>, i2
  %9 = arith.constant -1 : i2
  %10 = hw.array_get %0[%9] : !hw.array<4xi32>, i2
  %11 = phs.instance "acc1_pe_1" @acc1(%8, %10 : i32, i32) switches(%1 : index) -> i32
  %12 = phs.instance "acc1_pe_2" @acc1(%6, %11 : i32, i32) switches(%1 : index) -> i32
  phs.yield %12 : i32
}

// Single PE module
// CHECK: hw.module private @acc1(in %0 data_0: i32, in %1 data_1: i32, in %2 switch_0: i1, out out_0: i32)

// Reduction tree array: scalar output, inter-PE wiring
// CHECK: hw.module @acc1_array(in %0 data_0: !hw.array<4xi32>, in %1 switch_0: i1, out out_0: i32) {
// CHECK:   hw.instance "acc1_pe_0" @acc1
// CHECK:   hw.instance "acc1_pe_1" @acc1
// CHECK:   hw.instance "acc1_pe_2" @acc1
// CHECK:   hw.output %{{.*}} : i32
// CHECK: }

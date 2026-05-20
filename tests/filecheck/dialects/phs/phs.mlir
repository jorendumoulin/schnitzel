// RUN: XDSL_ROUNDTRIP
// RUN: XDSL_SINGLETRIP

phs.pe @myfirstaccelerator with %0, %1, %2, %3, %4, %5 (%6: f32, %7: f32) {
  %8 = phs.choose @_0 with %0 (%6: f32, %7: f32) -> f32
    0) (%9, %10) {
      %11 = arith.mulf %9, %10 : f32
      phs.yield %11 : f32
    }
    1) (%12, %13) {
      %14 = arith.addf %12, %13 : f32
      phs.yield %14 : f32
    }
    2) (%15, %16) {
      %17 = arith.subf %15, %16 : f32
      phs.yield %17 : f32
    }
  %9 = phs.choose @_1 with %1 (%6: f32, %8: f32) -> f32
    0) (%10, %11) {
      %12 = arith.mulf %10, %11 : f32
      phs.yield %12 : f32
    }
    1) (%13, %14) {
      %15 = arith.addf %13, %14 : f32
      phs.yield %15 : f32
    }
  %10 = phs.mux with %2 (%8 : f32, %9 : f32) -> f32
  %11 = phs.mux with %5 (%9 : f32, %7 : f32) -> f32
  %12 = phs.choose @_2 with %3 (%8: f32, %11: f32) -> f32
    0) (%13, %14) {
      %15 = arith.mulf %13, %14 : f32
      phs.yield %15 : f32
    }
    1) (%16, %17) {
      %18 = arith.divf %16, %17 : f32
      phs.yield %18 : f32
    }
  %13 = phs.mux with %4 (%10 : f32, %12 : f32) -> f32
  phs.yield %13 : f32
}


phs.pe @myfirstswitchlessaccelerator (%0: i32, %1: i32) {
  %2 = arith.muli %0, %1 : i32
  phs.yield %2 : i32
}

phs.pe_array @myarray targets @myfirstswitchlessaccelerator(%0: !hw.array<2xi32>) -> (!hw.array<2xi32>) attributes {bounds = array<i64: 2>, num_pure_inputs = 2 : i64, paired_outputs = array<i64>, input_modes = [[affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>]], output_modes = [[affine_map<(d0) -> (d0)>]]} {
  %1 = arith.constant 0 : i1
  %2 = hw.array_get %0[%1] : !hw.array<2xi32>, i1
  %3 = phs.instance "pe_0" @myfirstswitchlessaccelerator(%2, %2 : i32, i32) -> i32
  %4 = arith.constant 1 : i1
  %5 = hw.array_get %0[%4] : !hw.array<2xi32>, i1
  %6 = phs.instance "pe_1" @myfirstswitchlessaccelerator(%5, %5 : i32, i32) -> i32
  %7 = hw.array_create %6, %3 : i32
  phs.yield %7 : !hw.array<2xi32>
}

// Structured form with pe_ref + bounds + per-mode affine maps
phs.pe_array @myarray_structured targets @myfirstswitchlessaccelerator(%0: !hw.array<2xi32>, %1: !hw.array<2xi32>) -> (!hw.array<2xi32>) attributes {bounds = array<i64: 2>, num_pure_inputs = 2 : i64, paired_outputs = array<i64>, input_modes = [[affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>]], output_modes = [[affine_map<(d0) -> (d0)>]]} {
  %2 = arith.constant 0 : i1
  %3 = hw.array_get %0[%2] : !hw.array<2xi32>, i1
  %4 = hw.array_get %1[%2] : !hw.array<2xi32>, i1
  %5 = phs.instance "pe_0" @myfirstswitchlessaccelerator(%3, %4 : i32, i32) -> i32
  %6 = arith.constant 1 : i1
  %7 = hw.array_get %0[%6] : !hw.array<2xi32>, i1
  %8 = hw.array_get %1[%6] : !hw.array<2xi32>, i1
  %9 = phs.instance "pe_1" @myfirstswitchlessaccelerator(%7, %8 : i32, i32) -> i32
  %10 = hw.array_create %9, %5 : i32
  phs.yield %10 : !hw.array<2xi32>
}

// CHECK: builtin.module {
// CHECK-NEXT:   phs.pe @myfirstaccelerator with %0, %1, %2, %3, %4, %5 (%6: f32, %7: f32) {
// CHECK-NEXT:     %8 = phs.choose @_0 with %0 (%6: f32, %7: f32) -> f32
// CHECK-NEXT:       0) (%9, %10) {
// CHECK-NEXT:         %11 = arith.mulf %9, %10 : f32
// CHECK-NEXT:         phs.yield %11 : f32
// CHECK-NEXT:       }
// CHECK-NEXT:       1) (%12, %13) {
// CHECK-NEXT:         %14 = arith.addf %12, %13 : f32
// CHECK-NEXT:         phs.yield %14 : f32
// CHECK-NEXT:       }
// CHECK-NEXT:       2) (%15, %16) {
// CHECK-NEXT:         %17 = arith.subf %15, %16 : f32
// CHECK-NEXT:         phs.yield %17 : f32
// CHECK-NEXT:       }
// CHECK-NEXT:     %9 = phs.choose @_1 with %1 (%6: f32, %8: f32) -> f32
// CHECK-NEXT:       0) (%10, %11) {
// CHECK-NEXT:         %12 = arith.mulf %10, %11 : f32
// CHECK-NEXT:         phs.yield %12 : f32
// CHECK-NEXT:       }
// CHECK-NEXT:       1) (%13, %14) {
// CHECK-NEXT:         %15 = arith.addf %13, %14 : f32
// CHECK-NEXT:         phs.yield %15 : f32
// CHECK-NEXT:       }
// CHECK-NEXT:     %10 = phs.mux with %2 (%8 : f32, %9 : f32) -> f32
// CHECK-NEXT:     %11 = phs.mux with %5 (%9 : f32, %7 : f32) -> f32
// CHECK-NEXT:     %12 = phs.choose @_2 with %3 (%8: f32, %11: f32) -> f32
// CHECK-NEXT:       0) (%13, %14) {
// CHECK-NEXT:         %15 = arith.mulf %13, %14 : f32
// CHECK-NEXT:         phs.yield %15 : f32
// CHECK-NEXT:       }
// CHECK-NEXT:       1) (%16, %17) {
// CHECK-NEXT:         %18 = arith.divf %16, %17 : f32
// CHECK-NEXT:         phs.yield %18 : f32
// CHECK-NEXT:       }
// CHECK-NEXT:     %13 = phs.mux with %4 (%10 : f32, %12 : f32) -> f32
// CHECK-NEXT:     phs.yield %13 : f32
// CHECK-NEXT:   }
// CHECK-NEXT:   phs.pe @myfirstswitchlessaccelerator (%0: i32, %1: i32) {
// CHECK-NEXT:     %2 = arith.muli %0, %1 : i32
// CHECK-NEXT:     phs.yield %2 : i32
// CHECK-NEXT:   }
// CHECK-NEXT:   phs.pe_array @myarray targets @myfirstswitchlessaccelerator(%0: !hw.array<2xi32>) -> (!hw.array<2xi32>)
// CHECK:          phs.instance "pe_0" @myfirstswitchlessaccelerator
// CHECK:          phs.instance "pe_1" @myfirstswitchlessaccelerator
// CHECK:          phs.yield
// CHECK:        phs.pe_array @myarray_structured targets @myfirstswitchlessaccelerator
// CHECK-SAME:     bounds = array<i64: 2>
// CHECK-SAME:     num_pure_inputs = 2
// CHECK-SAME:     input_modes = {{\[}}{{\[}}affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>{{\]}}{{\]}}
// CHECK-SAME:     output_modes = {{\[}}{{\[}}affine_map<(d0) -> (d0)>{{\]}}{{\]}}
// CHECK:        phs.yield
// CHECK-NEXT:   }
// CHECK-NEXT: }

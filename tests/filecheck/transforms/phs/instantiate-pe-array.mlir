// RUN: snax-opt %s -p instantiate-pe-array | filecheck %s

// With a matching linalg.generic, instantiate-pe-array builds a phs.pe_array
// carrying the affine maps + bounds from the linalg, populates pe_ref, bounds,
// num_pure_inputs, paired_outputs, input_modes, output_modes, max_outputs.

phs.pe @myacc (%0: i32, %1: i32) {
  %2 = arith.muli %0, %1 : i32
  phs.yield %2 : i32
}
func.func @host(%a: memref<4xi32>, %b: memref<4xi32>, %c: memref<4xi32>) {
  linalg.generic {
    indexing_maps = [affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>],
    iterator_types = ["parallel"]
  } ins(%a, %b : memref<4xi32>, memref<4xi32>) outs(%c : memref<4xi32>) attrs = {phs_acc = @myacc, phs_array_bounds = array<i64: 4>} {
    ^bb(%a0: i32, %b0: i32, %c0: i32):
      %m = arith.muli %a0, %b0 : i32
      linalg.yield %m : i32
  }
  func.return
}

// CHECK:      phs.pe_array @myacc_array targets @myacc
// CHECK-SAME:   bounds = array<i64: 4>
// CHECK-SAME:   num_pure_inputs = 1
// CHECK-SAME:   paired_outputs = array<i64: 0>
// CHECK-SAME:   input_modes = {{\[}}{{\[}}affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>{{\]}}{{\]}}
// CHECK-SAME:   output_modes = {{\[}}{{\[}}affine_map<(d0) -> (d0)>{{\]}}{{\]}}

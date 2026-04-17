// RUN: snax-opt %s -p phs-encode --split-input-file | filecheck %s

// Two linalg.generics that target the SAME accelerator (@acc1) but have
// different operand arities:
//   Mode A: parallel add   c[i] = a[i] + b[i]          (2 ins, 1 outs)
//   Mode B: temporal accum c[i] += a[t, i]             (1 ins, 1 outs)
//
// After encoding + merging, a SINGLE phs.pe @acc1 should emerge with 3 data
// block args — the union of Mode A's inputs. Mode B gets a dead block-arg
// inserted at position 1 (for the missing second input). The merge's
// uncollide_inputs logic then places a phs.mux on the differing operand
// position so both modes share one arith.addi instance.

#map_1d   = affine_map<(d0) -> (d0)>
#map_a_2d = affine_map<(d0, d1) -> (d0, d1)>
#map_c_2d = affine_map<(d0, d1) -> (d1)>

func.func @mode_a(%arg0: tensor<?xi32>, %arg1: tensor<?xi32>) -> tensor<?xi32> {
  %c0 = arith.constant 0 : index
  %dim = tensor.dim %arg0, %c0 : tensor<?xi32>
  %init = tensor.empty(%dim) : tensor<?xi32>
  %r = linalg.generic {
    indexing_maps = [#map_1d, #map_1d, #map_1d],
    iterator_types = ["parallel"]
  } ins(%arg0, %arg1 : tensor<?xi32>, tensor<?xi32>)
    outs(%init : tensor<?xi32>) attrs = {"phs_acc" = @acc1} {
  ^bb0(%a: i32, %b: i32, %c: i32):
    %s = arith.addi %a, %b : i32
    linalg.yield %s : i32
  } -> tensor<?xi32>
  return %r : tensor<?xi32>
}

func.func @mode_b(%arg0: tensor<?x?xi32>, %arg1: tensor<?xi32>) -> tensor<?xi32> {
  %r = linalg.generic {
    indexing_maps = [#map_a_2d, #map_c_2d],
    iterator_types = ["reduction", "parallel"]
  } ins(%arg0 : tensor<?x?xi32>) outs(%arg1 : tensor<?xi32>) attrs = {"phs_acc" = @acc1} {
  ^bb0(%a: i32, %c: i32):
    %s = arith.addi %a, %c : i32
    linalg.yield %s : i32
  } -> tensor<?xi32>
  return %r : tensor<?xi32>
}

// Merged PE has 3 data block args (a, b/dead, c) plus a choose-switch plus a
// mux-switch added when Mode B gets uncollided against Mode A. A single
// phs.mux selects the second operand for arith.addi from either %b (mode A)
// or %c (mode B); both modes share ONE arith.addi instance inside the choose.
//
// CHECK-LABEL: phs.pe @acc1
// CHECK-SAME: with %{{[^ ,]+}}, %{{[^ ]+}} (%{{[^ ]+}} : i32, %{{[^ ]+}} : i32, %{{[^ ]+}} : i32) {
// CHECK:        phs.mux with
// CHECK:        phs.choose @i_i32_i32_o_i32_0
// CHECK:          arith.addi
// CHECK:          phs.yield
// CHECK:        phs.yield
// CHECK-NEXT:  }

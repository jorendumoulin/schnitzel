// RUN: snax-opt %s -p phs-schedule-separate-linalg --split-input-file | filecheck %s

// Each unannotated linalg.generic gets a unique @accN symbol plus the
// hardcoded array bounds attr.

#map = affine_map<(d0, d1) -> (d0, d1)>
func.func @two_generics(%arg0: tensor<4x4xf32>, %arg1: tensor<4x4xf32>) -> tensor<4x4xf32> {
  %init = tensor.empty() : tensor<4x4xf32>
  %0 = linalg.generic {
    indexing_maps = [#map, #map, #map],
    iterator_types = ["parallel", "parallel"]
  } ins(%arg0, %arg1 : tensor<4x4xf32>, tensor<4x4xf32>)
    outs(%init : tensor<4x4xf32>) {
  ^bb0(%a: f32, %b: f32, %_: f32):
    %s = arith.addf %a, %b : f32
    linalg.yield %s : f32
  } -> tensor<4x4xf32>
  %1 = linalg.generic {
    indexing_maps = [#map, #map],
    iterator_types = ["parallel", "parallel"]
  } ins(%0 : tensor<4x4xf32>)
    outs(%init : tensor<4x4xf32>) {
  ^bb0(%x: f32, %_: f32):
    linalg.yield %x : f32
  } -> tensor<4x4xf32>
  return %1 : tensor<4x4xf32>
}

// CHECK-LABEL: @two_generics
// CHECK: linalg.generic
// CHECK-SAME: phs_acc = @acc0
// CHECK-SAME: phs_array_bounds = array<i64: 4>
// CHECK: linalg.generic
// CHECK-SAME: phs_acc = @acc1
// CHECK-SAME: phs_array_bounds = array<i64: 4>

// -----

// Generics that already carry a phs_acc attr are left alone, and the counter
// keeps going for the unannotated ones.

#map = affine_map<(d0) -> (d0)>
func.func @keep_existing(%arg0: tensor<4xf32>) -> tensor<4xf32> {
  %init = tensor.empty() : tensor<4xf32>
  %0 = linalg.generic {
    indexing_maps = [#map, #map],
    iterator_types = ["parallel"]
  } ins(%arg0 : tensor<4xf32>) outs(%init : tensor<4xf32>) attrs = {phs_acc = @manual_acc} {
  ^bb0(%x: f32, %_: f32):
    linalg.yield %x : f32
  } -> tensor<4xf32>
  %1 = linalg.generic {
    indexing_maps = [#map, #map],
    iterator_types = ["parallel"]
  } ins(%0 : tensor<4xf32>) outs(%init : tensor<4xf32>) {
  ^bb0(%x: f32, %_: f32):
    linalg.yield %x : f32
  } -> tensor<4xf32>
  return %1 : tensor<4xf32>
}

// CHECK-LABEL: @keep_existing
// CHECK: linalg.generic
// CHECK-SAME: phs_acc = @manual_acc
// CHECK-NOT: phs_array_bounds
// CHECK: linalg.generic
// CHECK-SAME: phs_acc = @acc0
// CHECK-SAME: phs_array_bounds = array<i64: 4>

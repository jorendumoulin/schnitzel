// RUN: snax-opt --split-input-file -p promote-linalg-scalars %s | filecheck %s

// Scalar (non-shaped) `ins` operands of `linalg.generic` are promoted to a
// 0-rank shaped operand (`tensor<T>` / `memref<T>`). The indexing map is
// already the zero-result `(...) -> ()` broadcast and is left unchanged.
// After this pass every linalg/dart operand carries shape/layout, so
// downstream passes don't need a scalar branch.

// --- Tensor form -------------------------------------------------------

#map = affine_map<(d0) -> (d0)>
#mapS = affine_map<(d0) -> ()>
func.func @bias_tensor(%vec: tensor<16xi32>, %out: tensor<16xi32>) -> tensor<16xi32> {
  %bias = arith.constant 42 : i32
  %0 = linalg.generic {indexing_maps = [#map, #mapS, #map], iterator_types = ["parallel"]}
      ins(%vec, %bias : tensor<16xi32>, i32)
      outs(%out : tensor<16xi32>) {
  ^bb0(%a: i32, %b: i32, %o: i32):
    %s = arith.addi %a, %b : i32
    linalg.yield %s : i32
  } -> tensor<16xi32>
  return %0 : tensor<16xi32>
}

// CHECK-LABEL: @bias_tensor
// CHECK: %bias = arith.constant 42 : i32
// CHECK: %{{[0-9]+}} = tensor.from_elements %bias : tensor<i32>
// CHECK: linalg.generic {indexing_maps = [affine_map<(d0) -> (d0)>, affine_map<(d0) -> ()>, affine_map<(d0) -> (d0)>]
// CHECK-SAME: ins(%vec, %{{[0-9]+}} : tensor<16xi32>, tensor<i32>)

// -----

// --- MemRef form -------------------------------------------------------

#map_m = affine_map<(d0) -> (d0)>
#mapS_m = affine_map<(d0) -> ()>
func.func @bias_memref(%vec: memref<16xi32>, %out: memref<16xi32>) {
  %bias = arith.constant 42 : i32
  linalg.generic {indexing_maps = [#map_m, #mapS_m, #map_m], iterator_types = ["parallel"]}
      ins(%vec, %bias : memref<16xi32>, i32)
      outs(%out : memref<16xi32>) {
  ^bb0(%a: i32, %b: i32, %o: i32):
    %s = arith.addi %a, %b : i32
    linalg.yield %s : i32
  }
  return
}

// CHECK-LABEL: @bias_memref
// CHECK: %bias = arith.constant 42 : i32
// CHECK: %{{[0-9]+}} = memref.alloca() : memref<i32>
// CHECK: memref.store %bias, %{{[0-9]+}}[] : memref<i32>
// CHECK: linalg.generic {indexing_maps = [affine_map<(d0) -> (d0)>, affine_map<(d0) -> ()>, affine_map<(d0) -> (d0)>]
// CHECK-SAME: ins(%vec, %{{[0-9]+}} : memref<16xi32>, memref<i32>)

// -----

// --- Already shaped: no change -----------------------------------------

#map_n = affine_map<(d0) -> (d0)>
func.func @no_scalar(%a: tensor<16xi32>, %b: tensor<16xi32>, %out: tensor<16xi32>) -> tensor<16xi32> {
  %0 = linalg.generic {indexing_maps = [#map_n, #map_n, #map_n], iterator_types = ["parallel"]}
      ins(%a, %b : tensor<16xi32>, tensor<16xi32>)
      outs(%out : tensor<16xi32>) {
  ^bb0(%x: i32, %y: i32, %o: i32):
    %s = arith.addi %x, %y : i32
    linalg.yield %s : i32
  } -> tensor<16xi32>
  return %0 : tensor<16xi32>
}

// CHECK-LABEL: @no_scalar
// No tensor.from_elements / memref.alloca should be inserted.
// CHECK-NOT: tensor.from_elements
// CHECK-NOT: memref.alloca

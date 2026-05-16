// RUN: snax-opt %s -p phs-encode,instantiate-pe-array | filecheck %s

// Matmul-shaped kernel: 2x2 PE array with K folded into a temporal carry.
// Inputs A and B have broadcast affine maps that drop one of the spatial
// dims, exercising both:
//   - the wiring layer (port narrowing + same SSA value fanned to multiple
//     PEs along the dropped dim),
//   - the per-streamer mask emission (one bit per streamer-dim, set if the
//     corresponding map result depends on any iter dim).

#map_a = affine_map<(d0, d1) -> (d0)>      // broadcast along d1
#map_b = affine_map<(d0, d1) -> (d1)>      // broadcast along d0
#map_c = affine_map<(d0, d1) -> (d0, d1)>

func.func @matmul_broadcast(%a: tensor<2xi32>, %b: tensor<2xi32>, %c: tensor<2x2xi32>) -> tensor<2x2xi32> {
  %r = linalg.generic {
    indexing_maps = [#map_a, #map_b, #map_c],
    iterator_types = ["parallel", "parallel"]
  } ins(%a, %b : tensor<2xi32>, tensor<2xi32>)
    outs(%c : tensor<2x2xi32>) attrs = {phs_acc = @matmul_pe, phs_array_bounds = array<i64: 2, 2>} {
  ^bb0(%x: i32, %y: i32, %acc: i32):
    %p = arith.muli %x, %y : i32
    %s = arith.addi %acc, %p : i32
    linalg.yield %s : i32
  } -> tensor<2x2xi32>
  return %r : tensor<2x2xi32>
}

// Port shapes: A and B come in as 1-D arrays (dropped dim → narrow port);
// C is the full 2-D readWrite carry.
// CHECK: phs.pe_array @matmul_pe_array(%{{.*}} : !hw.array<2xi32>, %{{.*}} : !hw.array<2xi32>, %{{.*}} : !hw.array<2x!hw.array<2xi32>>, %{{.*}} : index, %{{.*}} : index) -> (!hw.array<2x!hw.array<2xi32>>, i1, i1, i2, i1)

// PE(0,0): A[0], B[0]  -- both indices come from the broadcast map.
// PE(0,1): A[0], B[1]  -- same A wire reused (broadcast along d1).
// PE(1,0): A[1], B[0]  -- same B[0] wire reused (broadcast along d0).
// PE(1,1): A[1], B[1].

// Mask emission. The streamer-mask block sits between the final hw.array_create
// (which packs the output) and the carry_used computation. Order in the yield
// is [data_array, A_mask, B_mask, C_mask, carry_used_C]. Expected values:
//   - A: 1-bit, streamer-dim 0 active → 1 (true).
//   - B: 1-bit, streamer-dim 0 active → 1 (true).  Pre-fix this was 0/false
//        because the bit was indexed by iter-dim 1 instead of streamer-dim 0,
//        and got clamped to 0 by the 1-bit width.
//   - C: 2-bit, both dims active → 0b11 (-1 : i2).
// CHECK:      %{{.+}} = hw.array_create %{{.+}}, %{{.+}} : !hw.array<2xi32>
// CHECK-NEXT: %[[A_MASK:.+]] = arith.constant true
// CHECK-NEXT: %[[B_MASK:.+]] = arith.constant true
// CHECK-NEXT: %{{.+}} = arith.constant -1 : i2
// CHECK:      phs.yield %{{.+}}, %[[A_MASK]], %[[B_MASK]], %{{.+}}, %{{.+}} : !hw.array<2x!hw.array<2xi32>>, i1, i1, i2, i1

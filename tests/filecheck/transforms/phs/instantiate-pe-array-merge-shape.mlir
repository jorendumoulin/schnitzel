// RUN: snax-opt %s -p phs-encode,instantiate-pe-array | filecheck %s

// Multi-mode merge with differing input shapes per mode.
// Mode 0 (matmul-tiled, K is a temporal carry): bounds (M,N), inputs broadcast
//        - A: (d0,d1)->(d0)        — 1D in this mode
//        - B: (d0,d1)->(d1)        — 1D in this mode
// Mode 1 (2D elementwise add):
//        - A,B: (d0,d1)->(d0,d1)   — full 2D
// Both modes: C: (d0,d1)->(d0,d1) (temporal carry / direct write).
//
// Per-operand union of access dims widens A and B to 2-D ports. Matmul mode
// achieves broadcast at runtime via stride-0 on the unused dim; 2D-add mode
// uses both dims fully. The PE-array instantiation is single-shape; per-mode
// behaviour is selected by the merged choose/mux switches in the PE body and
// by per-mode streamer config (set by software).

#map_a_mm = affine_map<(d0, d1) -> (d0)>
#map_b_mm = affine_map<(d0, d1) -> (d1)>
#map_id   = affine_map<(d0, d1) -> (d0, d1)>

func.func @merged(%am: tensor<2xi32>, %bm: tensor<2xi32>, %cm: tensor<2x2xi32>,
                  %ae: tensor<2x2xi32>, %be: tensor<2x2xi32>, %ce: tensor<2x2xi32>)
    -> (tensor<2x2xi32>, tensor<2x2xi32>) {
  %r1 = linalg.generic {
    indexing_maps = [#map_a_mm, #map_b_mm, #map_id],
    iterator_types = ["parallel", "parallel"]
  } ins(%am, %bm : tensor<2xi32>, tensor<2xi32>)
    outs(%cm : tensor<2x2xi32>) attrs = {phs_acc = @acc, phs_array_bounds = array<i64: 2, 2>} {
  ^bb0(%x: i32, %y: i32, %acc: i32):
    %p = arith.muli %x, %y : i32
    %s = arith.addi %acc, %p : i32
    linalg.yield %s : i32
  } -> tensor<2x2xi32>

  %r2 = linalg.generic {
    indexing_maps = [#map_id, #map_id, #map_id],
    iterator_types = ["parallel", "parallel"]
  } ins(%ae, %be : tensor<2x2xi32>, tensor<2x2xi32>)
    outs(%ce : tensor<2x2xi32>) attrs = {phs_acc = @acc} {
  ^bb1(%x: i32, %y: i32, %out: i32):
    %s = arith.addi %x, %y : i32
    linalg.yield %s : i32
  } -> tensor<2x2xi32>

  return %r1, %r2 : tensor<2x2xi32>, tensor<2x2xi32>
}

// All three operand ports are 2-D (the union of mode 0's narrow shape and
// mode 1's full identity). Without union widening, mode 0 would give A and
// B 1-D ports, and merging mode 1 in would fail with a shape mismatch.
// CHECK: phs.pe_array @acc_array(%{{.*}} : !hw.array<2x!hw.array<2xi32>>, %{{.*}} : !hw.array<2x!hw.array<2xi32>>, %{{.*}} : !hw.array<2x!hw.array<2xi32>>, %{{.*}} : index, %{{.*}} : index, %{{.*}} : index) -> (!hw.array<2x!hw.array<2xi32>>, i2, i2, i2, i1)

// Each PE reads a 2D position from each of A, B, C. In matmul mode the
// streamer's stride-0 setup makes the d1 reads of A return the same value
// (broadcast) and likewise for B over d0; in 2D-add mode all reads are
// distinct.
// CHECK: phs.instance "acc_pe_0_0" @acc(%{{.+}}, %{{.+}}, %{{.+}} : i32, i32, i32)
// CHECK: phs.instance "acc_pe_0_1" @acc(%{{.+}}, %{{.+}}, %{{.+}} : i32, i32, i32)
// CHECK: phs.instance "acc_pe_1_0" @acc(%{{.+}}, %{{.+}}, %{{.+}} : i32, i32, i32)
// CHECK: phs.instance "acc_pe_1_1" @acc(%{{.+}}, %{{.+}}, %{{.+}} : i32, i32, i32)

// Streamer masks are the OR-across-modes superset (both modes vectorised
// in any dim → all bits on). Per-mode broadcast is handled by stride
// configuration, not by the static mask.
// CHECK: %{{.+}} = arith.constant -1 : i2
// CHECK-NEXT: %{{.+}} = arith.constant -1 : i2
// CHECK-NEXT: %{{.+}} = arith.constant -1 : i2

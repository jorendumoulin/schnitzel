// RUN: snax-opt %s -p phs-encode,instantiate-pe-array | filecheck %s

// Multi-mode merge with differing OUTPUT shapes per mode.
// Mode 0 (3D matmul, K spatial reduction): bounds (M,N,K)
//   A: (d0,d1,d2)->(d0,d2)   B: (d0,d1,d2)->(d2,d1)
//   C: (d0,d1,d2)->(d0,d1)   — reduces along d2
// Mode 1 (3D elementwise add):
//   All operands identity (d0,d1,d2)->(d0,d1,d2) — no reduction
//
// Key cases this test pins:
//   1. The output port is widened to the union shape (M,N,K) — wider than
//      matmul's natural 2-D shape — so both modes share an array.
//   2. The K-reduction CHAIN is still wired (per-mode reduction detection
//      sees that matmul reduces, even though the union map is identity).
//      Elementwise mode bypasses the chain via the merged PE body's mux.
//   3. Output assembly with the union (identity) map is parallel — every
//      PE drives its own (d0,d1,d2) position. In matmul mode the writeback
//      streamer collapses K via stride 0 + last-write-wins; in elementwise
//      mode it uses full strides.
//   4. Carry input port also widens to 3-D to match output. Chain-init for
//      the matmul-mode head PE indexes the widened carry at full coords.

#map_a_mm = affine_map<(d0, d1, d2) -> (d0, d2)>
#map_b_mm = affine_map<(d0, d1, d2) -> (d2, d1)>
#map_c_mm = affine_map<(d0, d1, d2) -> (d0, d1)>
#map_3d   = affine_map<(d0, d1, d2) -> (d0, d1, d2)>

func.func @merged(%am: tensor<2x2xi32>, %bm: tensor<2x2xi32>, %cm: tensor<2x2xi32>,
                  %ae: tensor<2x2x2xi32>, %be: tensor<2x2x2xi32>, %ce: tensor<2x2x2xi32>)
    -> (tensor<2x2xi32>, tensor<2x2x2xi32>) {
  %r1 = linalg.generic {
    indexing_maps = [#map_a_mm, #map_b_mm, #map_c_mm],
    iterator_types = ["parallel", "parallel", "reduction"]
  } ins(%am, %bm : tensor<2x2xi32>, tensor<2x2xi32>)
    outs(%cm : tensor<2x2xi32>) attrs = {phs_acc = @acc, phs_array_bounds = array<i64: 2, 2, 2>} {
  ^bb0(%x: i32, %y: i32, %acc: i32):
    %p = arith.muli %x, %y : i32
    %s = arith.addi %acc, %p : i32
    linalg.yield %s : i32
  } -> tensor<2x2xi32>

  %r2 = linalg.generic {
    indexing_maps = [#map_3d, #map_3d, #map_3d],
    iterator_types = ["parallel", "parallel", "parallel"]
  } ins(%ae, %be : tensor<2x2x2xi32>, tensor<2x2x2xi32>)
    outs(%ce : tensor<2x2x2xi32>) attrs = {phs_acc = @acc} {
  ^bb1(%x: i32, %y: i32, %out: i32):
    %s = arith.addi %x, %y : i32
    linalg.yield %s : i32
  } -> tensor<2x2x2xi32>

  return %r1, %r2 : tensor<2x2xi32>, tensor<2x2x2xi32>
}

// All ports (including output and carry) are 3-D — the union of matmul's
// 2-D output with elementwise's 3-D identity output. Mask widths are i3,
// reflecting the 3-D streamer ports.
// CHECK: phs.pe_array @acc_array(%{{.*}} : !hw.array<2x!hw.array<2x!hw.array<2xi32>>>, %{{.*}} : !hw.array<2x!hw.array<2x!hw.array<2xi32>>>, %{{.*}} : !hw.array<2x!hw.array<2x!hw.array<2xi32>>>, %{{.*}} : index, %{{.*}} : index, %{{.*}} : index) -> (!hw.array<2x!hw.array<2x!hw.array<2xi32>>>, i3, i3, i3, i1)

// K-direction chain wiring (intersection-map grouping detects reduction
// even though union output_maps is identity):
//   PE(0,0,0) head → PE(0,0,1) takes its carry from PE(0,0,0)'s result.
// CHECK: %[[PE_0_0_0:.+]] = phs.instance "acc_pe_0_0_0"
// CHECK: %{{.+}} = phs.instance "acc_pe_0_0_1" @acc(%{{.+}}, %{{.+}}, %[[PE_0_0_0]] : i32, i32, i32)
// CHECK: %[[PE_0_1_0:.+]] = phs.instance "acc_pe_0_1_0"
// CHECK: %{{.+}} = phs.instance "acc_pe_0_1_1" @acc(%{{.+}}, %{{.+}}, %[[PE_0_1_0]] : i32, i32, i32)
// CHECK: %[[PE_1_0_0:.+]] = phs.instance "acc_pe_1_0_0"
// CHECK: %{{.+}} = phs.instance "acc_pe_1_0_1" @acc(%{{.+}}, %{{.+}}, %[[PE_1_0_0]] : i32, i32, i32)
// CHECK: %[[PE_1_1_0:.+]] = phs.instance "acc_pe_1_1_0"
// CHECK: %{{.+}} = phs.instance "acc_pe_1_1_1" @acc(%{{.+}}, %{{.+}}, %[[PE_1_1_0]] : i32, i32, i32)

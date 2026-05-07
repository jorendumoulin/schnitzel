// RUN: snax-opt %s -p phs-encode,instantiate-pe-array | filecheck %s

// Canonical 3D matmul: 3D iteration (M, N, K), 2D access on each operand,
// K-direction reduction. Bounds = [2, 2, 2] makes K a spatial chain dim:
// for each (d0, d1) output position there are K=2 PEs, and each PE feeds
// its accumulator output into the next PE's carry input.

#map_a = affine_map<(d0, d1, d2) -> (d0, d2)>   // broadcast along d1
#map_b = affine_map<(d0, d1, d2) -> (d2, d1)>   // broadcast along d0
#map_c = affine_map<(d0, d1, d2) -> (d0, d1)>   // reduction along d2

func.func @matmul(%a: tensor<2x2xi32>, %b: tensor<2x2xi32>, %c: tensor<2x2xi32>) -> tensor<2x2xi32> {
  %r = linalg.generic {
    indexing_maps = [#map_a, #map_b, #map_c],
    iterator_types = ["parallel", "parallel", "reduction"]
  } ins(%a, %b : tensor<2x2xi32>, tensor<2x2xi32>)
    outs(%c : tensor<2x2xi32>) attrs = {phs_acc = @matmul_pe, phs_array_bounds = array<i64: 2, 2, 2>} {
  ^bb0(%x: i32, %y: i32, %acc: i32):
    %p = arith.muli %x, %y : i32
    %s = arith.addi %acc, %p : i32
    linalg.yield %s : i32
  } -> tensor<2x2xi32>
  return %r : tensor<2x2xi32>
}

// All three operand ports are 2-D (M=N=K=2). The carry-input port for C
// is shaped like the output map (2D), not a scalar — the partial-reduction
// chain reads its initial value from C[d0,d1].
// CHECK: phs.pe_array @matmul_pe_array(%{{.*}} : !hw.array<2x!hw.array<2xi32>>, %{{.*}} : !hw.array<2x!hw.array<2xi32>>, %{{.*}} : !hw.array<2x!hw.array<2xi32>>, %{{.*}} : index, %{{.*}} : index) -> (!hw.array<2x!hw.array<2xi32>>, i2, i2, i2, i1)

// PE(0,0,0): chain head for output group (0,0). Carry comes from C[0,0]
// (a scalar produced by two array_get ops on the C input).
// CHECK: %[[PE_0_0_0:.+]] = phs.instance "matmul_pe_pe_0_0_0" @matmul_pe(%{{.+}}, %{{.+}}, %{{.+}} : i32, i32, i32)

// PE(0,0,1): chain step for group (0,0). Carry MUST be PE(0,0,0)'s result
// (not another C array_get).
// CHECK-NEXT: %{{.+}} = arith.constant
// CHECK: %{{.+}} = phs.instance "matmul_pe_pe_0_0_1" @matmul_pe(%{{.+}}, %{{.+}}, %[[PE_0_0_0]] : i32, i32, i32)

// PE(0,1,0): chain head for group (0,1). New initial value from C[0,1].
// CHECK: %[[PE_0_1_0:.+]] = phs.instance "matmul_pe_pe_0_1_0" @matmul_pe(%{{.+}}, %{{.+}}, %{{.+}} : i32, i32, i32)

// PE(0,1,1): chain step for group (0,1). Carry comes from PE(0,1,0).
// CHECK: %{{.+}} = phs.instance "matmul_pe_pe_0_1_1" @matmul_pe(%{{.+}}, %{{.+}}, %[[PE_0_1_0]] : i32, i32, i32)

// PE(1,0,0) and PE(1,1,0) are also chain heads for their groups.
// PE(1,0,1) and PE(1,1,1) chain from their respective heads.
// CHECK: %[[PE_1_0_0:.+]] = phs.instance "matmul_pe_pe_1_0_0"
// CHECK: %{{.+}} = phs.instance "matmul_pe_pe_1_0_1" @matmul_pe(%{{.+}}, %{{.+}}, %[[PE_1_0_0]] : i32, i32, i32)
// CHECK: %[[PE_1_1_0:.+]] = phs.instance "matmul_pe_pe_1_1_0"
// CHECK: %{{.+}} = phs.instance "matmul_pe_pe_1_1_1" @matmul_pe(%{{.+}}, %{{.+}}, %[[PE_1_1_0]] : i32, i32, i32)

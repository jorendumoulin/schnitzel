// Accelerator-free baseline. Structurally identical to streamer_phs_alu's
// kernel, but with no `phs_acc` / `phs_array_bounds` annotations, so
// PhsEncodePass builds no PEOp and phsc harvests zero accelerators.
//
// The result is a plain 2-core cluster: PhsDriver is called with
// `[[], []]` and the software below runs entirely on the RISC-V core.
// This is the CPU reference point every accelerated config is measured
// against.
#map = affine_map<(d0) -> (d0)>
module {
  func.func public @streamer_add(%arg0 : tensor<16xi32>, %arg1 : tensor<16xi32>) -> tensor<16xi32> {
    %empty = tensor.empty() : tensor<16xi32>
    %added = linalg.generic {indexing_maps = [#map, #map, #map], iterator_types = ["parallel"]}
        ins(%arg0, %arg1 : tensor<16xi32>, tensor<16xi32>)
        outs(%empty : tensor<16xi32>) {
    ^bb0(%in: i32, %in_0: i32, %out: i32):
      %s = arith.addi %in, %in_0 : i32
      linalg.yield %s : i32
    } -> tensor<16xi32>
    return %added : tensor<16xi32>
  }
}

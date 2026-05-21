// PHS kernel describing two distinct PE templates that the schnitzel HW
// generator should produce as two separate accelerators on core 1:
//   @acc1 : multi-option arithmetic PE  (addi / subi / muli)
//   @acc2 : xor PE                      (xori only)
//
// All four linalg.generic ops are tagged with phs_array_bounds = 4 so each
// PE is instantiated as a 4-wide spatial array. Within a single phs_acc
// symbol PhsEncodePass merges the encountered op kinds into one PEOp whose
// ChooseOps offer the union of their bodies — hence @acc1's main ChooseOp
// has three options (addi, subi, muli) selectable by a runtime switch.
#map = affine_map<(d0, d1) -> (d0, d1)>
module{
  func.func public @streamer_alu(%arg0 : tensor<16x4xi32>, %arg1 : tensor<16x4xi32>)
      -> (tensor<16x4xi32>, tensor<16x4xi32>) {
    %empty0 = tensor.empty() : tensor<16x4xi32>
    %added = linalg.generic {indexing_maps = [#map, #map, #map], iterator_types = ["parallel", "parallel"]}
        ins(%arg0, %arg1 : tensor<16x4xi32>, tensor<16x4xi32>)
        outs(%empty0 : tensor<16x4xi32>)
        attrs = {phs_acc = @acc1, phs_array_bounds = array<i64: 4, 2>} {
    ^bb0(%in: i32, %in_0: i32, %out: i32):
      %s = arith.addi %in, %in_0 : i32
      linalg.yield %s : i32
    } -> tensor<16x4xi32>
    %empty1 = tensor.empty() : tensor<16x4xi32>
    %subbed = linalg.generic {indexing_maps = [#map, #map, #map], iterator_types = ["parallel", "parallel"]}
        ins(%arg0, %arg1 : tensor<16x4xi32>, tensor<16x4xi32>)
        outs(%empty1 : tensor<16x4xi32>)
        attrs = {phs_acc = @acc1, phs_array_bounds = array<i64: 4, 2>} {
    ^bb0(%in: i32, %in_0: i32, %out: i32):
      %d = arith.subi %in, %in_0 : i32
      linalg.yield %d : i32
    } -> tensor<16x4xi32>
    return %added, %subbed : tensor<16x4xi32>, tensor<16x4xi32>
  }
}

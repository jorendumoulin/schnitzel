// PHS kernel exercising a 0-rank (scalar) broadcast operand on a streamer PE.
//
//   @acc1 : single-option addi PE with two i32 data inputs.
//
// The linalg.generic below has two ins — a 1-D vector and a scalar i32 — with
// the scalar carrying the broadcast indexing map `() -> ()`. PhsEncodePass
// shapes the PE from the body, treating the scalar as a 0-rank stream port.
#map = affine_map<(d0) -> (d0)>
#mapS = affine_map<(d0) -> ()>
module {
  func.func public @streamer_scalar_bias(%arg0 : tensor<16xi32>, %bias : i32) -> tensor<16xi32> {
    %empty = tensor.empty() : tensor<16xi32>
    %result = linalg.generic {indexing_maps = [#map, #mapS, #map], iterator_types = ["parallel"]}
        ins(%arg0, %bias : tensor<16xi32>, i32)
        outs(%empty : tensor<16xi32>)
        attrs = {phs_acc = @acc1, phs_array_bounds = array<i64: 4>} {
    ^bb0(%a: i32, %b: i32, %out: i32):
      %s = arith.addi %a, %b : i32
      linalg.yield %s : i32
    } -> tensor<16xi32>
    return %result : tensor<16xi32>
  }
}

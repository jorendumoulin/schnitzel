// Minimal building block from the ad01 anomaly-detection workload: a
// fully-connected-layer-style reduction. For every output column `i`, accumulate
// `A[t, i] * W[t, i]` along the temporal axis `t` into an initial carry `C[i]`.
// This pattern is the one PHS lowers via the readWrite streamer carry chain.

#map_in = affine_map<(d0, d1) -> (d0, d1)>
#map_out = affine_map<(d0, d1) -> (d1)>

module {
  func.func public @streamer_ad01(
      %arg0 : tensor<4x4xf32>,
      %arg1 : tensor<4x4xf32>,
      %arg2 : tensor<4xf32>) -> tensor<4xf32> {
    %result = linalg.generic {
      indexing_maps = [#map_in, #map_in, #map_out],
      iterator_types = ["reduction", "parallel"]
    } ins(%arg0, %arg1 : tensor<4x4xf32>, tensor<4x4xf32>) outs(%arg2 : tensor<4xf32>) attrs = {phs_acc = @acc1} {
    ^bb0(%a : f32, %w : f32, %c : f32):
      %m = arith.mulf %a, %w : f32
      %s = arith.addf %c, %m : f32
      linalg.yield %s : f32
    } -> tensor<4xf32>
    return %result : tensor<4xf32>
  }
}

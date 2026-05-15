// Two building blocks from the ad01 anomaly-detection workload, sharing the
// same PHS accelerator (@acc1):
//
//   1. FC-style reduction:  fc[i] = bias[i] + sum_t a[t, i] * w[t, i]
//   2. Clamp activation:    out[i] = max(min(fc[i], 30.0), 0.0)
//
// Both `linalg.generic` ops are annotated with `phs_acc = @acc1`, so the PHS
// encoder merges their bodies into a single multi-mode PE selected at runtime
// by the switch input. Clamp thresholds are plain `arith.constant` literals;
// the encoder's constant-sink step pulls them into each `phs.choose` region
// where they're used, so they lower to wired bit patterns inside the PE and
// don't consume PE input ports.

#map_in = affine_map<(d0, d1) -> (d0, d1)>
#map_out = affine_map<(d0, d1) -> (d1)>
#map_elt = affine_map<(d0) -> (d0)>

module {
  func.func public @streamer_ad01(
      %arg0 : tensor<4x4xf32>,
      %arg1 : tensor<4x4xf32>,
      %arg2 : tensor<4xf32>) -> tensor<4xf32> {
    %hi = arith.constant 3.000000e+01 : f32
    %lo = arith.constant 0.000000e+00 : f32

    // Layer 1: fully-connected reduction.
    %fc = linalg.generic {
      indexing_maps = [#map_in, #map_in, #map_out],
      iterator_types = ["reduction", "parallel"]
    } ins(%arg0, %arg1 : tensor<4x4xf32>, tensor<4x4xf32>) outs(%arg2 : tensor<4xf32>) attrs = {phs_acc = @acc1} {
    ^bb0(%a : f32, %w : f32, %c : f32):
      %m = arith.mulf %a, %w : f32
      %s = arith.addf %c, %m : f32
      linalg.yield %s : f32
    } -> tensor<4xf32>

    // Layer 2: clamp activation.
    %init = tensor.empty() : tensor<4xf32>
    %out = linalg.generic {
      indexing_maps = [#map_elt, #map_elt],
      iterator_types = ["parallel"]
    } ins(%fc : tensor<4xf32>) outs(%init : tensor<4xf32>) attrs = {phs_acc = @acc1} {
    ^bb0(%x : f32, %_ : f32):
      %clamped_hi = arith.minimumf %x, %hi : f32
      %clamped = arith.maximumf %clamped_hi, %lo : f32
      linalg.yield %clamped : f32
    } -> tensor<4xf32>

    return %out : tensor<4xf32>
  }
}

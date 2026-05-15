#map_in = affine_map<(d0, d1) -> (d0, d1)>
#map_out = affine_map<(d0, d1) -> (d1)>
#map_elt = affine_map<(d0) -> (d0)>

module {
  func.func public @streamer_ad01(
      %arg0: memref<4x4xf32>,
      %arg1: memref<4x4xf32>,
      %arg2: memref<4xf32>,
      %arg3: memref<4xf32>,
      %arg4: memref<4xf32>) {
    linalg.generic {
      indexing_maps = [#map_in, #map_in, #map_out],
      iterator_types = ["reduction", "parallel"]
    } ins(%arg0, %arg1 : memref<4x4xf32>, memref<4x4xf32>) outs(%arg2 : memref<4xf32>) {
    ^bb0(%a : f32, %w : f32, %c : f32):
      %m = arith.mulf %a, %w : f32
      %s = arith.addf %c, %m : f32
      linalg.yield %s : f32
    }

    linalg.generic {
      indexing_maps = [#map_elt, #map_elt, #map_elt, #map_elt],
      iterator_types = ["parallel"]
    } ins(%arg2, %arg3, %arg4 : memref<4xf32>, memref<4xf32>, memref<4xf32>) outs(%arg2 : memref<4xf32>) {
    ^bb0(%x : f32, %hi : f32, %lo : f32, %_ : f32):
      %clamped_hi = arith.minimumf %x, %hi : f32
      %clamped = arith.maximumf %clamped_hi, %lo : f32
      linalg.yield %clamped : f32
    }
    return
  }
}

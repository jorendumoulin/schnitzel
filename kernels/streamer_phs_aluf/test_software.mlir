#map = affine_map<(d0) -> (d0)>
module {
  func.func public @streamer_add(%arg0: memref<16xf32>, %arg1: memref<16xf32>, %arg2: memref<16xf32>) {
    linalg.generic {indexing_maps = [#map, #map, #map], iterator_types = ["parallel"]} ins(%arg0, %arg1 : memref<16xf32>, memref<16xf32>) outs(%arg2 : memref<16xf32>) {
    ^bb0(%in: f32, %in_0: f32, %out: f32):
      %0 = arith.addf %in, %in_0 : f32
      linalg.yield %0 : f32
    }
    return
  }
}

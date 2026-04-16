#map_a = affine_map<(d0, d1) -> (d0, d1)>
#map_c = affine_map<(d0, d1) -> (d1)>
module {
  func.func public @streamer_acc(%arg0: memref<4x4xi32>, %arg1: memref<4xi32>) {
    linalg.generic {
      indexing_maps = [#map_a, #map_c],
      iterator_types = ["reduction", "parallel"]
    } ins(%arg0 : memref<4x4xi32>) outs(%arg1 : memref<4xi32>) {
    ^bb0(%in: i32, %out: i32):
      %s = arith.addi %in, %out : i32
      linalg.yield %s : i32
    }
    return
  }
}

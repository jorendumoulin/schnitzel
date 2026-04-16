#map_a = affine_map<(d0, d1) -> (d0, d1)>
#map_c = affine_map<(d0, d1) -> (d1)>
module{
  func.func public @streamer_acc(%arg0 : tensor<4x4xi32>, %arg1 : tensor<4xi32>) -> tensor<4xi32>{
    %result = linalg.generic {
      indexing_maps = [#map_a, #map_c],
      iterator_types = ["reduction", "parallel"]
    } ins(%arg0 : tensor<4x4xi32>) outs(%arg1 : tensor<4xi32>) attrs = {phs_acc = @acc1} {
    ^bb0(%in: i32, %out: i32):
      %s = arith.addi %in, %out : i32
      linalg.yield %s : i32
    } -> tensor<4xi32>
    return %result : tensor<4xi32>
  }
}

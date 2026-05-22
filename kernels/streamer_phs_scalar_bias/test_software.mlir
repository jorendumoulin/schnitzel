// SW kernel: O = A + bias, where bias is a constant i32 broadcast onto every
// lane via the indexing map `() -> ()`. Exercises the 0-rank scalar operand
// path through convert-linalg-to-dart, dart_bufferize, dart_scheduler, and
// convert-dart-to-snax-stream.
#map = affine_map<(d0) -> (d0)>
#mapS = affine_map<(d0) -> ()>
module {
  func.func public @streamer_scalar_bias(%arg0: memref<16xi32>, %arg1: memref<16xi32>) {
    %bias = arith.constant 42 : i32
    linalg.generic {indexing_maps = [#map, #mapS, #map], iterator_types = ["parallel"]}
        ins(%arg0, %bias : memref<16xi32>, i32)
        outs(%arg1 : memref<16xi32>) {
    ^bb0(%a: i32, %b: i32, %out: i32):
      %s = arith.addi %a, %b : i32
      linalg.yield %s : i32
    }
    return
  }
}

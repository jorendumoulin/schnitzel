// SW kernel exercising both PHS accelerators on core 1 with two
// independent operations:
//   D = A + B   (auto-dispatched to @acc1, the addi PE)
//   O = A ^ B   (auto-dispatched to @acc2, the xori PE)
#map = affine_map<(d0) -> (d0)>
module {
  func.func public @streamer_add(%arg0: memref<16xi32>, %arg1: memref<16xi32>, %arg2: memref<16xi32>, %arg3: memref<16xi32>) {
    linalg.generic {indexing_maps = [#map, #map, #map], iterator_types = ["parallel"]}
        ins(%arg0, %arg1 : memref<16xi32>, memref<16xi32>)
        outs(%arg2 : memref<16xi32>) {
    ^bb0(%in: i32, %in_0: i32, %out: i32):
      %0 = arith.addi %in, %in_0 : i32
      linalg.yield %0 : i32
    }
    linalg.generic {indexing_maps = [#map, #map, #map], iterator_types = ["parallel"]}
        ins(%arg0, %arg1 : memref<16xi32>, memref<16xi32>)
        outs(%arg3 : memref<16xi32>) {
    ^bb0(%in: i32, %in_0: i32, %out: i32):
      %1 = arith.xori %in, %in_0 : i32
      linalg.yield %1 : i32
    }
    return
  }
}

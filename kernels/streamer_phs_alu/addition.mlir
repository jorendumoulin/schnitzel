#map = affine_map<(d0) -> (d0)>
module{
  func.func public @streamer_add(%arg0 : tensor<16xi32>, %arg1 : tensor<16xi32>) -> tensor<16xi32>{
    %empty = tensor.empty() : tensor<16xi32>
    %added = linalg.add ins(%arg0, %arg1 : tensor<16xi32>, tensor<16xi32>) outs(%empty: tensor<16xi32>) -> tensor<16xi32>
    %empty1 = tensor.empty() : tensor<16xi32>
    %subbed = linalg.sub ins(%arg0, %added: tensor<16xi32>, tensor<16xi32>) outs(%empty1: tensor<16xi32>) -> tensor<16xi32>
    %empty2 = tensor.empty() : tensor<16xi32>
    %mul = linalg.mul ins(%arg0, %subbed: tensor<16xi32>, tensor<16xi32>) outs(%empty2: tensor<16xi32>) -> tensor<16xi32>
    %empty3 = tensor.empty() : tensor<16xi32>
    %xori = linalg.generic {indexing_maps = [#map, #map, #map], iterator_types = ["parallel"]} ins(%arg0, %mul : tensor<16xi32>, tensor<16xi32>) outs(%empty3 : tensor<16xi32>) attrs =  {phs_acc = @acc1} {
    ^bb0(%in: i32, %in_0: i32, %out: i32):
      %2 = arith.xori %in, %in_0 : i32
      linalg.yield %2 : i32
    } -> tensor<16xi32>
    return %xori : tensor<16xi32>
  }
}

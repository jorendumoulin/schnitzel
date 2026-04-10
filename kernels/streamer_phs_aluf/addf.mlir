module {
  func.func public @streamer_add(%arg0: tensor<16xf32>, %arg1: tensor<16xf32>) -> tensor<16xf32> {
    %0 = tensor.empty() : tensor<16xf32>
    %1 = linalg.add ins(%arg0, %arg1 : tensor<16xf32>, tensor<16xf32>) outs(%0 : tensor<16xf32>) -> tensor<16xf32>
    %2 = linalg.sub ins(%arg0, %1 : tensor<16xf32>, tensor<16xf32>) outs(%0 : tensor<16xf32>) -> tensor<16xf32>
    %3 = linalg.mul ins(%arg0, %2 : tensor<16xf32>, tensor<16xf32>) outs(%0 : tensor<16xf32>) -> tensor<16xf32>
    return %3 : tensor<16xf32>
  }
}

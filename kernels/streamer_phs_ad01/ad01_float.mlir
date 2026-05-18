#map = affine_map<()[s0] -> (s0 * 640)>
#map1 = affine_map<(d0, d1, d2, d3) -> (d3)>
#map2 = affine_map<(d0, d1, d2, d3) -> (d0, d1, d2, d3)>
#map3 = affine_map<(d0, d1, d2, d3, d4, d5, d6) -> (d0, d1 + d4, d2 + d5, d6)>
#map4 = affine_map<(d0, d1, d2, d3, d4, d5, d6) -> (d3, d4, d5, d6)>
#map5 = affine_map<(d0, d1, d2, d3, d4, d5, d6) -> (d0, d1, d2, d3)>
#map6 = affine_map<(d0, d1) -> (d0, d1)>
#map7 = affine_map<()[s0] -> (s0 * 128)>
#map8 = affine_map<()[s0] -> (s0 * 8)>
module {
  func.func @main(%arg0: tensor<?x640xf32> {ml_program.identifier = "input_1"}) -> (tensor<?x640xf32> {ml_program.identifier = "Identity"}) {
    %c8 = arith.constant 8 : index
    %cst = arith.constant 3.40282347E+38 : f32
    %cst_0 = arith.constant 0.000000e+00 : f32
    %c128 = arith.constant 128 : index
    %c640 = arith.constant 640 : index
    %cst_1 = arith.constant dense<1.000000e+00> : tensor<640x1x1x128xf32>
    %cst_2 = arith.constant dense<2.000000e+00> : tensor<128x1x1x128xf32>
    %cst_3 = arith.constant dense<3.000000e+00> : tensor<128x1x1x128xf32>
    %cst_4 = arith.constant dense<4.000000e+00> : tensor<128x1x1x128xf32>
    %cst_5 = arith.constant dense<5.000000e+00> : tensor<128x1x1x8xf32>
    %cst_6 = arith.constant dense<6.000000e+00> : tensor<8x1x1x128xf32>
    %cst_7 = arith.constant dense<7.000000e+00> : tensor<128x1x1x128xf32>
    %cst_8 = arith.constant dense<8.000000e+00> : tensor<128x1x1x128xf32>
    %cst_9 = arith.constant dense<9.000000e+00> : tensor<128x1x1x128xf32>
    %cst_10 = arith.constant dense<1.000000e+01> : tensor<128x1x1x640xf32>
    %cst_11 = arith.constant dense<1.100000e+01> : tensor<640xf32>
    %cst_12 = arith.constant dense<1.200000e+01> : tensor<128xf32>
    %cst_13 = arith.constant dense<1.300000e+01> : tensor<128xf32>
    %cst_14 = arith.constant dense<1.400000e+01> : tensor<128xf32>
    %cst_15 = arith.constant dense<1.500000e+01> : tensor<128xf32>
    %cst_16 = arith.constant dense<1.600000e+01> : tensor<8xf32>
    %cst_17 = arith.constant dense<1.700000e+01> : tensor<128xf32>
    %cst_18 = arith.constant dense<1.800000e+01> : tensor<128xf32>
    %cst_19 = arith.constant dense<1.900000e+01> : tensor<128xf32>
    %cst_20 = arith.constant dense<2.000000e+01> : tensor<128xf32>
    %c0 = arith.constant 0 : index
    %dim = tensor.dim %arg0, %c0 : tensor<?x640xf32>
    %0 = affine.apply #map()[%dim]
    %1 = arith.divui %0, %c640 : index
    %expanded = tensor.expand_shape %arg0 [[0], [1, 2, 3]] output_shape [%1, 1, 1, 640] : tensor<?x640xf32> into tensor<?x1x1x640xf32>
    %dim_21 = tensor.dim %arg0, %c0 : tensor<?x640xf32>
    %2 = tensor.empty(%dim_21) : tensor<?x1x1x128xf32>
    %3 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_20 : tensor<128xf32>) outs(%2 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x128xf32>
    %4 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded, %cst_10 : tensor<?x1x1x640xf32>, tensor<128x1x1x640xf32>) outs(%3 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x128xf32>
    %collapsed = tensor.collapse_shape %4 [[0], [1, 2, 3]] : tensor<?x1x1x128xf32> into tensor<?x128xf32>
    %5 = tensor.empty(%dim_21) : tensor<?x128xf32>
    %6 = linalg.generic {indexing_maps = [#map6, #map6], iterator_types = ["parallel", "parallel"]} ins(%collapsed : tensor<?x128xf32>) outs(%5 : tensor<?x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      %68 = arith.minimumf %in, %cst : f32
      %69 = arith.maximumf %68, %cst_0 : f32
      linalg.yield %69 : f32
    } -> tensor<?x128xf32>
    %7 = affine.apply #map7()[%dim_21]
    %8 = arith.divui %7, %c128 : index
    %expanded_22 = tensor.expand_shape %6 [[0], [1, 2, 3]] output_shape [%8, 1, 1, 128] : tensor<?x128xf32> into tensor<?x1x1x128xf32>
    %9 = tensor.empty(%dim_21) : tensor<?x1x1x128xf32>
    %10 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_19 : tensor<128xf32>) outs(%9 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x128xf32>
    %11 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded_22, %cst_9 : tensor<?x1x1x128xf32>, tensor<128x1x1x128xf32>) outs(%10 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x128xf32>
    %collapsed_23 = tensor.collapse_shape %11 [[0], [1, 2, 3]] : tensor<?x1x1x128xf32> into tensor<?x128xf32>
    %12 = tensor.empty(%dim_21) : tensor<?x128xf32>
    %13 = linalg.generic {indexing_maps = [#map6, #map6], iterator_types = ["parallel", "parallel"]} ins(%collapsed_23 : tensor<?x128xf32>) outs(%12 : tensor<?x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      %68 = arith.minimumf %in, %cst : f32
      %69 = arith.maximumf %68, %cst_0 : f32
      linalg.yield %69 : f32
    } -> tensor<?x128xf32>
    %14 = affine.apply #map7()[%dim_21]
    %15 = arith.divui %14, %c128 : index
    %expanded_24 = tensor.expand_shape %13 [[0], [1, 2, 3]] output_shape [%15, 1, 1, 128] : tensor<?x128xf32> into tensor<?x1x1x128xf32>
    %16 = tensor.empty(%dim_21) : tensor<?x1x1x128xf32>
    %17 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_18 : tensor<128xf32>) outs(%16 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x128xf32>
    %18 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded_24, %cst_8 : tensor<?x1x1x128xf32>, tensor<128x1x1x128xf32>) outs(%17 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x128xf32>
    %collapsed_25 = tensor.collapse_shape %18 [[0], [1, 2, 3]] : tensor<?x1x1x128xf32> into tensor<?x128xf32>
    %19 = tensor.empty(%dim_21) : tensor<?x128xf32>
    %20 = linalg.generic {indexing_maps = [#map6, #map6], iterator_types = ["parallel", "parallel"]} ins(%collapsed_25 : tensor<?x128xf32>) outs(%19 : tensor<?x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      %68 = arith.minimumf %in, %cst : f32
      %69 = arith.maximumf %68, %cst_0 : f32
      linalg.yield %69 : f32
    } -> tensor<?x128xf32>
    %21 = affine.apply #map7()[%dim_21]
    %22 = arith.divui %21, %c128 : index
    %expanded_26 = tensor.expand_shape %20 [[0], [1, 2, 3]] output_shape [%22, 1, 1, 128] : tensor<?x128xf32> into tensor<?x1x1x128xf32>
    %23 = tensor.empty(%dim_21) : tensor<?x1x1x128xf32>
    %24 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_17 : tensor<128xf32>) outs(%23 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x128xf32>
    %25 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded_26, %cst_7 : tensor<?x1x1x128xf32>, tensor<128x1x1x128xf32>) outs(%24 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x128xf32>
    %collapsed_27 = tensor.collapse_shape %25 [[0], [1, 2, 3]] : tensor<?x1x1x128xf32> into tensor<?x128xf32>
    %26 = tensor.empty(%dim_21) : tensor<?x128xf32>
    %27 = linalg.generic {indexing_maps = [#map6, #map6], iterator_types = ["parallel", "parallel"]} ins(%collapsed_27 : tensor<?x128xf32>) outs(%26 : tensor<?x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      %68 = arith.minimumf %in, %cst : f32
      %69 = arith.maximumf %68, %cst_0 : f32
      linalg.yield %69 : f32
    } -> tensor<?x128xf32>
    %28 = affine.apply #map7()[%dim_21]
    %29 = arith.divui %28, %c128 : index
    %expanded_28 = tensor.expand_shape %27 [[0], [1, 2, 3]] output_shape [%29, 1, 1, 128] : tensor<?x128xf32> into tensor<?x1x1x128xf32>
    %30 = tensor.empty(%dim_21) : tensor<?x1x1x8xf32>
    %31 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_16 : tensor<8xf32>) outs(%30 : tensor<?x1x1x8xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x8xf32>
    %32 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded_28, %cst_6 : tensor<?x1x1x128xf32>, tensor<8x1x1x128xf32>) outs(%31 : tensor<?x1x1x8xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x8xf32>
    %collapsed_29 = tensor.collapse_shape %32 [[0], [1, 2, 3]] : tensor<?x1x1x8xf32> into tensor<?x8xf32>
    %33 = tensor.empty(%dim_21) : tensor<?x8xf32>
    %34 = linalg.generic {indexing_maps = [#map6, #map6], iterator_types = ["parallel", "parallel"]} ins(%collapsed_29 : tensor<?x8xf32>) outs(%33 : tensor<?x8xf32>) {
    ^bb0(%in: f32, %out: f32):
      %68 = arith.minimumf %in, %cst : f32
      %69 = arith.maximumf %68, %cst_0 : f32
      linalg.yield %69 : f32
    } -> tensor<?x8xf32>
    %35 = affine.apply #map8()[%dim_21]
    %36 = arith.divui %35, %c8 : index
    %expanded_30 = tensor.expand_shape %34 [[0], [1, 2, 3]] output_shape [%36, 1, 1, 8] : tensor<?x8xf32> into tensor<?x1x1x8xf32>
    %37 = tensor.empty(%dim_21) : tensor<?x1x1x128xf32>
    %38 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_15 : tensor<128xf32>) outs(%37 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x128xf32>
    %39 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded_30, %cst_5 : tensor<?x1x1x8xf32>, tensor<128x1x1x8xf32>) outs(%38 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x128xf32>
    %collapsed_31 = tensor.collapse_shape %39 [[0], [1, 2, 3]] : tensor<?x1x1x128xf32> into tensor<?x128xf32>
    %40 = tensor.empty(%dim_21) : tensor<?x128xf32>
    %41 = linalg.generic {indexing_maps = [#map6, #map6], iterator_types = ["parallel", "parallel"]} ins(%collapsed_31 : tensor<?x128xf32>) outs(%40 : tensor<?x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      %68 = arith.minimumf %in, %cst : f32
      %69 = arith.maximumf %68, %cst_0 : f32
      linalg.yield %69 : f32
    } -> tensor<?x128xf32>
    %42 = affine.apply #map7()[%dim_21]
    %43 = arith.divui %42, %c128 : index
    %expanded_32 = tensor.expand_shape %41 [[0], [1, 2, 3]] output_shape [%43, 1, 1, 128] : tensor<?x128xf32> into tensor<?x1x1x128xf32>
    %44 = tensor.empty(%dim_21) : tensor<?x1x1x128xf32>
    %45 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_14 : tensor<128xf32>) outs(%44 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x128xf32>
    %46 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded_32, %cst_4 : tensor<?x1x1x128xf32>, tensor<128x1x1x128xf32>) outs(%45 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x128xf32>
    %collapsed_33 = tensor.collapse_shape %46 [[0], [1, 2, 3]] : tensor<?x1x1x128xf32> into tensor<?x128xf32>
    %47 = tensor.empty(%dim_21) : tensor<?x128xf32>
    %48 = linalg.generic {indexing_maps = [#map6, #map6], iterator_types = ["parallel", "parallel"]} ins(%collapsed_33 : tensor<?x128xf32>) outs(%47 : tensor<?x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      %68 = arith.minimumf %in, %cst : f32
      %69 = arith.maximumf %68, %cst_0 : f32
      linalg.yield %69 : f32
    } -> tensor<?x128xf32>
    %49 = affine.apply #map7()[%dim_21]
    %50 = arith.divui %49, %c128 : index
    %expanded_34 = tensor.expand_shape %48 [[0], [1, 2, 3]] output_shape [%50, 1, 1, 128] : tensor<?x128xf32> into tensor<?x1x1x128xf32>
    %51 = tensor.empty(%dim_21) : tensor<?x1x1x128xf32>
    %52 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_13 : tensor<128xf32>) outs(%51 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x128xf32>
    %53 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded_34, %cst_3 : tensor<?x1x1x128xf32>, tensor<128x1x1x128xf32>) outs(%52 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x128xf32>
    %collapsed_35 = tensor.collapse_shape %53 [[0], [1, 2, 3]] : tensor<?x1x1x128xf32> into tensor<?x128xf32>
    %54 = tensor.empty(%dim_21) : tensor<?x128xf32>
    %55 = linalg.generic {indexing_maps = [#map6, #map6], iterator_types = ["parallel", "parallel"]} ins(%collapsed_35 : tensor<?x128xf32>) outs(%54 : tensor<?x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      %68 = arith.minimumf %in, %cst : f32
      %69 = arith.maximumf %68, %cst_0 : f32
      linalg.yield %69 : f32
    } -> tensor<?x128xf32>
    %56 = affine.apply #map7()[%dim_21]
    %57 = arith.divui %56, %c128 : index
    %expanded_36 = tensor.expand_shape %55 [[0], [1, 2, 3]] output_shape [%57, 1, 1, 128] : tensor<?x128xf32> into tensor<?x1x1x128xf32>
    %58 = tensor.empty(%dim_21) : tensor<?x1x1x128xf32>
    %59 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_12 : tensor<128xf32>) outs(%58 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x128xf32>
    %60 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded_36, %cst_2 : tensor<?x1x1x128xf32>, tensor<128x1x1x128xf32>) outs(%59 : tensor<?x1x1x128xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x128xf32>
    %collapsed_37 = tensor.collapse_shape %60 [[0], [1, 2, 3]] : tensor<?x1x1x128xf32> into tensor<?x128xf32>
    %61 = tensor.empty(%dim_21) : tensor<?x128xf32>
    %62 = linalg.generic {indexing_maps = [#map6, #map6], iterator_types = ["parallel", "parallel"]} ins(%collapsed_37 : tensor<?x128xf32>) outs(%61 : tensor<?x128xf32>) {
    ^bb0(%in: f32, %out: f32):
      %68 = arith.minimumf %in, %cst : f32
      %69 = arith.maximumf %68, %cst_0 : f32
      linalg.yield %69 : f32
    } -> tensor<?x128xf32>
    %63 = affine.apply #map7()[%dim_21]
    %64 = arith.divui %63, %c128 : index
    %expanded_38 = tensor.expand_shape %62 [[0], [1, 2, 3]] output_shape [%64, 1, 1, 128] : tensor<?x128xf32> into tensor<?x1x1x128xf32>
    %65 = tensor.empty(%dim_21) : tensor<?x1x1x640xf32>
    %66 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_11 : tensor<640xf32>) outs(%65 : tensor<?x1x1x640xf32>) {
    ^bb0(%in: f32, %out: f32):
      linalg.yield %in : f32
    } -> tensor<?x1x1x640xf32>
    %67 = linalg.generic {indexing_maps = [#map3, #map4, #map5], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded_38, %cst_1 : tensor<?x1x1x128xf32>, tensor<640x1x1x128xf32>) outs(%66 : tensor<?x1x1x640xf32>) {
    ^bb0(%in: f32, %in_40: f32, %out: f32):
      %68 = arith.mulf %in, %in_40 : f32
      %69 = arith.addf %out, %68 : f32
      linalg.yield %69 : f32
    } -> tensor<?x1x1x640xf32>
    %collapsed_39 = tensor.collapse_shape %67 [[0], [1, 2, 3]] : tensor<?x1x1x640xf32> into tensor<?x640xf32>
    return %collapsed_39 : tensor<?x640xf32>
  }
}



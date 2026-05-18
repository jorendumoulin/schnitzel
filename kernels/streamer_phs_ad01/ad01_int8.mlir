#map = affine_map<()[s0] -> (s0 * 640)>
#map1 = affine_map<(d0, d1, d2, d3) -> (d3)>
#map2 = affine_map<(d0, d1, d2, d3) -> (d0, d1, d2, d3)>
#map3 = affine_map<(d0, d1, d2, d3, d4, d5, d6) -> (d0, d1 + d4, d2 + d5, d6)>
#map4 = affine_map<(d0, d1, d2, d3, d4, d5, d6) -> (d3, d4, d5, d6)>
#map5 = affine_map<(d0, d1, d2, d3, d4, d5, d6) -> ()>
#map6 = affine_map<(d0, d1, d2, d3, d4, d5, d6) -> (d0, d1, d2, d3)>
module {
  func.func @main(%arg0: tensor<?x640xi8> {ml_program.identifier = "input_1"}) -> (tensor<?x640xi8> {ml_program.identifier = "Identity"}) {
    %c549755813888_i64 = arith.constant 549755813888 : i64
    %c40_i64 = arith.constant 40 : i64
    %c1462485049_i64 = arith.constant 1462485049 : i64
    %c1105921578_i64 = arith.constant 1105921578 : i64
    %c1994356874_i64 = arith.constant 1994356874 : i64
    %c1315670656_i64 = arith.constant 1315670656 : i64
    %c1442237646_i64 = arith.constant 1442237646 : i64
    %c68719476736_i64 = arith.constant 68719476736 : i64
    %c37_i64 = arith.constant 37 : i64
    %c1085889731_i64 = arith.constant 1085889731 : i64
    %c17179869184_i64 = arith.constant 17179869184 : i64
    %c35_i64 = arith.constant 35 : i64
    %c1439819856_i64 = arith.constant 1439819856 : i64
    %c4294967296_i64 = arith.constant 4294967296 : i64
    %c33_i64 = arith.constant 33 : i64
    %c1185020333_i64 = arith.constant 1185020333 : i64
    %c34359738368_i64 = arith.constant 34359738368 : i64
    %c36_i64 = arith.constant 36 : i64
    %c1442659867_i64 = arith.constant 1442659867 : i64
    %c274877906944_i64 = arith.constant 274877906944 : i64
    %c39_i64 = arith.constant 39 : i64
    %c1638001719_i64 = arith.constant 1638001719 : i64
    %c96_i32 = arith.constant 96 : i32
    %c127_i32 = arith.constant 127 : i32
    %c-1073741824_i64 = arith.constant -1073741824 : i64
    %c1073741824_i64 = arith.constant 1073741824 : i64
    %c-128_i32 = arith.constant -128 : i32
    %c0_i32 = arith.constant 0 : i32
    %c89_i32 = arith.constant 89 : i32
    %c640 = arith.constant 640 : index
    %cst = arith.constant dense<1> : tensor<640x1x1x128xi8>
    %cst_0 = arith.constant dense<2> : tensor<128x1x1x128xi8>
    %cst_1 = arith.constant dense<3> : tensor<128x1x1x128xi8>
    %cst_2 = arith.constant dense<4> : tensor<128x1x1x128xi8>
    %cst_3 = arith.constant dense<5> : tensor<128x1x1x8xi8>
    %cst_4 = arith.constant dense<6> : tensor<8x1x1x128xi8>
    %cst_5 = arith.constant dense<7> : tensor<128x1x1x128xi8>
    %cst_6 = arith.constant dense<8> : tensor<128x1x1x128xi8>
    %cst_7 = arith.constant dense<9> : tensor<128x1x1x128xi8>
    %cst_8 = arith.constant dense<10> : tensor<128x1x1x640xi8>
    %cst_9 = arith.constant dense<11> : tensor<640xi32>
    %cst_10 = arith.constant dense<12> : tensor<128xi32>
    %cst_11 = arith.constant dense<13> : tensor<128xi32>
    %cst_12 = arith.constant dense<14> : tensor<128xi32>
    %cst_13 = arith.constant dense<15> : tensor<128xi32>
    %cst_14 = arith.constant dense<16> : tensor<8xi32>
    %cst_15 = arith.constant dense<17> : tensor<128xi32>
    %cst_16 = arith.constant dense<18> : tensor<128xi32>
    %cst_17 = arith.constant dense<19> : tensor<128xi32>
    %cst_18 = arith.constant dense<20> : tensor<128xi32>
    %c0 = arith.constant 0 : index
    %dim = tensor.dim %arg0, %c0 : tensor<?x640xi8>
    %0 = affine.apply #map()[%dim]
    %1 = arith.divui %0, %c640 : index
    %expanded = tensor.expand_shape %arg0 [[0], [1, 2, 3]] output_shape [%1, 1, 1, 640] : tensor<?x640xi8> into tensor<?x1x1x640xi8>
    %dim_19 = tensor.dim %arg0, %c0 : tensor<?x640xi8>
    %2 = tensor.empty(%dim_19) : tensor<?x1x1x128xi32>
    %3 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_18 : tensor<128xi32>) outs(%2 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x128xi32>
    %4 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%expanded, %cst_8, %c89_i32, %c0_i32 : tensor<?x1x1x640xi8>, tensor<128x1x1x640xi8>, i32, i32) outs(%3 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x128xi32>
    %5 = tensor.empty(%dim_19) : tensor<?x1x1x128xi8>
    %6 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%4 : tensor<?x1x1x128xi32>) outs(%5 : tensor<?x1x1x128xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1638001719_i64 : i64
      %54 = arith.addi %53, %c274877906944_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c39_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c-128_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x128xi8>
    %7 = tensor.empty(%dim_19) : tensor<?x1x1x128xi32>
    %8 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_17 : tensor<128xi32>) outs(%7 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x128xi32>
    %9 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%6, %cst_7, %c-128_i32, %c0_i32 : tensor<?x1x1x128xi8>, tensor<128x1x1x128xi8>, i32, i32) outs(%8 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x128xi32>
    %10 = tensor.empty(%dim_19) : tensor<?x1x1x128xi8>
    %11 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%9 : tensor<?x1x1x128xi32>) outs(%10 : tensor<?x1x1x128xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1442659867_i64 : i64
      %54 = arith.addi %53, %c34359738368_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c36_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c-128_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x128xi8>
    %12 = tensor.empty(%dim_19) : tensor<?x1x1x128xi32>
    %13 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_16 : tensor<128xi32>) outs(%12 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x128xi32>
    %14 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%11, %cst_6, %c-128_i32, %c0_i32 : tensor<?x1x1x128xi8>, tensor<128x1x1x128xi8>, i32, i32) outs(%13 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x128xi32>
    %15 = tensor.empty(%dim_19) : tensor<?x1x1x128xi8>
    %16 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%14 : tensor<?x1x1x128xi32>) outs(%15 : tensor<?x1x1x128xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1185020333_i64 : i64
      %54 = arith.addi %53, %c4294967296_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c33_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c-128_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x128xi8>
    %17 = tensor.empty(%dim_19) : tensor<?x1x1x128xi32>
    %18 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_15 : tensor<128xi32>) outs(%17 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x128xi32>
    %19 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%16, %cst_5, %c-128_i32, %c0_i32 : tensor<?x1x1x128xi8>, tensor<128x1x1x128xi8>, i32, i32) outs(%18 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x128xi32>
    %20 = tensor.empty(%dim_19) : tensor<?x1x1x128xi8>
    %21 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%19 : tensor<?x1x1x128xi32>) outs(%20 : tensor<?x1x1x128xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1439819856_i64 : i64
      %54 = arith.addi %53, %c17179869184_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c35_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c-128_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x128xi8>
    %22 = tensor.empty(%dim_19) : tensor<?x1x1x8xi32>
    %23 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_14 : tensor<8xi32>) outs(%22 : tensor<?x1x1x8xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x8xi32>
    %24 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%21, %cst_4, %c-128_i32, %c0_i32 : tensor<?x1x1x128xi8>, tensor<8x1x1x128xi8>, i32, i32) outs(%23 : tensor<?x1x1x8xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x8xi32>
    %25 = tensor.empty(%dim_19) : tensor<?x1x1x8xi8>
    %26 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%24 : tensor<?x1x1x8xi32>) outs(%25 : tensor<?x1x1x8xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1085889731_i64 : i64
      %54 = arith.addi %53, %c68719476736_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c37_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c-128_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x8xi8>
    %27 = tensor.empty(%dim_19) : tensor<?x1x1x128xi32>
    %28 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_13 : tensor<128xi32>) outs(%27 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x128xi32>
    %29 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%26, %cst_3, %c-128_i32, %c0_i32 : tensor<?x1x1x8xi8>, tensor<128x1x1x8xi8>, i32, i32) outs(%28 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x128xi32>
    %30 = tensor.empty(%dim_19) : tensor<?x1x1x128xi8>
    %31 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%29 : tensor<?x1x1x128xi32>) outs(%30 : tensor<?x1x1x128xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1442237646_i64 : i64
      %54 = arith.addi %53, %c34359738368_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c36_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c-128_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x128xi8>
    %32 = tensor.empty(%dim_19) : tensor<?x1x1x128xi32>
    %33 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_12 : tensor<128xi32>) outs(%32 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x128xi32>
    %34 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%31, %cst_2, %c-128_i32, %c0_i32 : tensor<?x1x1x128xi8>, tensor<128x1x1x128xi8>, i32, i32) outs(%33 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x128xi32>
    %35 = tensor.empty(%dim_19) : tensor<?x1x1x128xi8>
    %36 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%34 : tensor<?x1x1x128xi32>) outs(%35 : tensor<?x1x1x128xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1315670656_i64 : i64
      %54 = arith.addi %53, %c34359738368_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c36_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c-128_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x128xi8>
    %37 = tensor.empty(%dim_19) : tensor<?x1x1x128xi32>
    %38 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_11 : tensor<128xi32>) outs(%37 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x128xi32>
    %39 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%36, %cst_1, %c-128_i32, %c0_i32 : tensor<?x1x1x128xi8>, tensor<128x1x1x128xi8>, i32, i32) outs(%38 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x128xi32>
    %40 = tensor.empty(%dim_19) : tensor<?x1x1x128xi8>
    %41 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%39 : tensor<?x1x1x128xi32>) outs(%40 : tensor<?x1x1x128xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1994356874_i64 : i64
      %54 = arith.addi %53, %c68719476736_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c37_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c-128_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x128xi8>
    %42 = tensor.empty(%dim_19) : tensor<?x1x1x128xi32>
    %43 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_10 : tensor<128xi32>) outs(%42 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x128xi32>
    %44 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%41, %cst_0, %c-128_i32, %c0_i32 : tensor<?x1x1x128xi8>, tensor<128x1x1x128xi8>, i32, i32) outs(%43 : tensor<?x1x1x128xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x128xi32>
    %45 = tensor.empty(%dim_19) : tensor<?x1x1x128xi8>
    %46 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%44 : tensor<?x1x1x128xi32>) outs(%45 : tensor<?x1x1x128xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1105921578_i64 : i64
      %54 = arith.addi %53, %c68719476736_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c37_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c-128_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x128xi8>
    %47 = tensor.empty(%dim_19) : tensor<?x1x1x640xi32>
    %48 = linalg.generic {indexing_maps = [#map1, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%cst_9 : tensor<640xi32>) outs(%47 : tensor<?x1x1x640xi32>) {
    ^bb0(%in: i32, %out: i32):
      linalg.yield %in : i32
    } -> tensor<?x1x1x640xi32>
    %49 = linalg.generic {indexing_maps = [#map3, #map4, #map5, #map5, #map6], iterator_types = ["parallel", "parallel", "parallel", "parallel", "reduction", "reduction", "reduction"]} ins(%46, %cst, %c-128_i32, %c0_i32 : tensor<?x1x1x128xi8>, tensor<640x1x1x128xi8>, i32, i32) outs(%48 : tensor<?x1x1x640xi32>) {
    ^bb0(%in: i8, %in_20: i8, %in_21: i32, %in_22: i32, %out: i32):
      %52 = arith.extsi %in : i8 to i32
      %53 = arith.subi %52, %in_21 : i32
      %54 = arith.extsi %in_20 : i8 to i32
      %55 = arith.subi %54, %in_22 : i32
      %56 = arith.muli %53, %55 : i32
      %57 = arith.addi %out, %56 : i32
      linalg.yield %57 : i32
    } -> tensor<?x1x1x640xi32>
    %50 = tensor.empty(%dim_19) : tensor<?x1x1x640xi8>
    %51 = linalg.generic {indexing_maps = [#map2, #map2], iterator_types = ["parallel", "parallel", "parallel", "parallel"]} ins(%49 : tensor<?x1x1x640xi32>) outs(%50 : tensor<?x1x1x640xi8>) {
    ^bb0(%in: i32, %out: i8):
      %52 = arith.extsi %in : i32 to i64
      %53 = arith.muli %52, %c1462485049_i64 : i64
      %54 = arith.addi %53, %c549755813888_i64 : i64
      %55 = arith.cmpi sge, %in, %c0_i32 : i32
      %56 = arith.select %55, %c1073741824_i64, %c-1073741824_i64 : i64
      %57 = arith.addi %56, %54 : i64
      %58 = arith.shrsi %57, %c40_i64 : i64
      %59 = arith.trunci %58 : i64 to i32
      %60 = arith.addi %59, %c96_i32 : i32
      %61 = arith.maxsi %60, %c-128_i32 : i32
      %62 = arith.minsi %61, %c127_i32 : i32
      %63 = arith.trunci %62 : i32 to i8
      linalg.yield %63 : i8
    } -> tensor<?x1x1x640xi8>
    %collapsed = tensor.collapse_shape %51 [[0], [1, 2, 3]] : tensor<?x1x1x640xi8> into tensor<?x640xi8>
    return %collapsed : tensor<?x640xi8>
  }
}



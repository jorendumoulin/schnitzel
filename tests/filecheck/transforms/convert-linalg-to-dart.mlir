// RUN: snax-opt --split-input-file -p convert-linalg-to-dart %s | filecheck %s

// After 9a62afc, scalar (i32) ins on a streamable linalg.generic become
// 0-rank broadcast stream ports on the dart.operation rather than
// outer-scope SSA values: their `() -> ()` indexing map carries broadcast
// semantics and operandSegmentSizes counts them as inputs.

%arg0, %arg1, %arg2 = "test.op"() : () -> (tensor<16x16xi8>, tensor<16x16xi8>, tensor<16x16xi32>)
%c0_i32 = arith.constant 0 : i32
// CHECK: builtin.module {
// CHECK-NEXT:  %arg0, %arg1, %arg2 = "test.op"() : () -> (tensor<16x16xi8>, tensor<16x16xi8>, tensor<16x16xi32>)
// CHECK-NEXT:  %c0_i32 = arith.constant 0 : i32

%0 = tensor.empty() : tensor<16x16xi32>
// CHECK-NEXT:  %0 = tensor.empty() : tensor<16x16xi32>

%1 = linalg.generic {indexing_maps = [affine_map<(d0, d1, d2) -> (d0, d2)>, affine_map<(d0, d1, d2) -> (d2, d1)>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> (d0, d1)>], iterator_types = ["parallel", "parallel", "reduction"], library_call = "snax_gemmx_stream"} ins(%arg0, %arg1, %c0_i32, %c0_i32 : tensor<16x16xi8>, tensor<16x16xi8>, i32, i32) outs(%0 : tensor<16x16xi32>) {
^bb0(%in: i8, %in_1: i8, %in_2: i32, %in_3: i32, %out: i32):
  %2 = kernel.qmac %in, %in_1 zp_lhs : %in_2 zp_rhs : %in_3 : i8, i8, i32, i32 -> i32
  linalg.yield %2 : i32
} -> tensor<16x16xi32>
// CHECK-NEXT: %1 = "dart.operation"(%arg0, %arg1, %c0_i32, %c0_i32, %0) <{patterns = [affine_map<(d0, d1, d2) -> (d0, d2)>, affine_map<(d0, d1, d2) -> (d2, d1)>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> (d0, d1)>], accelerator = "snax_gemmx", operandSegmentSizes = array<i32: 4, 1>}> ({
// CHECK-NEXT: ^bb0(%2: !dart.stream<i8>, %3: !dart.stream<i8>, %4: !dart.stream<i32>, %5: !dart.stream<i32>, %6: !dart.stream<i32>):
// CHECK-NEXT:   %7 = "dart.generic"(%2, %3, %4, %5) <{library_call = "snax_gemmx"}> ({
// CHECK-NEXT:   ^bb1(%in: i8, %in_1: i8, %in_2: i32, %in_3: i32, %out: i32):
// CHECK-NEXT:     %8 = kernel.qmac %in, %in_1 zp_lhs : %in_2 zp_rhs : %in_3 : i8, i8, i32, i32 -> i32
// CHECK-NEXT:     dart.yield %8 : i32
// CHECK-NEXT:   }) : (!dart.stream<i8>, !dart.stream<i8>, !dart.stream<i32>, !dart.stream<i32>) -> !dart.stream<i32>
// CHECK-NEXT:   dart.yield %7 : !dart.stream<i32>
// CHECK-NEXT: }) : (tensor<16x16xi8>, tensor<16x16xi8>, i32, i32, tensor<16x16xi32>) -> tensor<16x16xi32>

%3 = tensor.empty() : tensor<16x16xi32>
//CHECK-NEXT:   %9 = tensor.empty() : tensor<16x16xi32>

%4 = linalg.generic {indexing_maps = [affine_map<(d0, d1) -> (d0, d1)>, affine_map<(d0, d1) -> (d0, d1)>, affine_map<(d0, d1) -> (d0, d1)>], iterator_types = ["parallel", "parallel"], library_call = "snax_gemmx_stream"} ins(%1, %arg2 : tensor<16x16xi32>, tensor<16x16xi32>) outs(%3 : tensor<16x16xi32>) {
^bb1(%in_4: i32, %in_5: i32, %out_1: i32):
  %5 = kernel.add %in_4, %in_5 : i32, i32 -> i32
  linalg.yield %5 : i32
} -> tensor<16x16xi32>

//CHECK-NEXT: %10 = "dart.operation"(%1, %arg2, %9) <{patterns = [affine_map<(d0, d1) -> (d0, d1)>, affine_map<(d0, d1) -> (d0, d1)>, affine_map<(d0, d1) -> (d0, d1)>], accelerator = "snax_gemmx", operandSegmentSizes = array<i32: 2, 1>}> ({
//CHECK-NEXT: ^bb2(%11: !dart.stream<i32>, %12: !dart.stream<i32>, %13: !dart.stream<i32>):
//CHECK-NEXT:   %14 = "dart.generic"(%11, %12) <{library_call = "snax_gemmx"}> ({
//CHECK-NEXT:   ^bb3(%in_4: i32, %in_5: i32, %out_1: i32):
//CHECK-NEXT:     %15 = kernel.add %in_4, %in_5 : i32, i32 -> i32
//CHECK-NEXT:     dart.yield %15 : i32
//CHECK-NEXT:   }) : (!dart.stream<i32>, !dart.stream<i32>) -> !dart.stream<i32>
//CHECK-NEXT:   dart.yield %14 : !dart.stream<i32>
//CHECK-NEXT: }) : (tensor<16x16xi32>, tensor<16x16xi32>, tensor<16x16xi32>) -> tensor<16x16xi32>

%6 = arith.constant dense<5> : tensor<16x16xi32>
//CHECK-NEXT:  %16 = arith.constant dense<5> : tensor<16x16xi32>

%7 = linalg.generic {indexing_maps = [affine_map<(d0, d1, d2) -> (d0, d2)>, affine_map<(d0, d1, d2) -> (d2, d1)>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> (d0, d1)>], iterator_types = ["parallel", "parallel", "reduction"], library_call = "snax_gemmx_stream"} ins(%arg0, %arg1, %c0_i32, %c0_i32 : tensor<16x16xi8>, tensor<16x16xi8>, i32, i32) outs(%6 : tensor<16x16xi32>) {
^bb0(%in_6: i8, %in_7: i8, %in_8: i32, %in_9: i32, %out_2: i32):
  %8 = kernel.qmac %in_6, %in_7 zp_lhs : %in_8 zp_rhs : %in_9 : i8, i8, i32, i32 -> i32
  linalg.yield %8 : i32
} -> tensor<16x16xi32>

//CHECK-NEXT:  %17 = "dart.operation"(%arg0, %arg1, %c0_i32, %c0_i32, %16) <{patterns = [affine_map<(d0, d1, d2) -> (d0, d2)>, affine_map<(d0, d1, d2) -> (d2, d1)>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> (d0, d1)>], accelerator = "snax_gemmx", operandSegmentSizes = array<i32: 4, 1>}> ({
//CHECK-NEXT:  ^bb4(%18: !dart.stream<i8>, %19: !dart.stream<i8>, %20: !dart.stream<i32>, %21: !dart.stream<i32>, %22: !dart.stream<i32>):
//CHECK-NEXT:    %23 = "dart.generic"(%18, %19, %20, %21) <{library_call = "snax_gemmx"}> ({
//CHECK-NEXT:    ^bb5(%in_6: i8, %in_7: i8, %in_8: i32, %in_9: i32, %out_2: i32):
//CHECK-NEXT:      %24 = kernel.qmac %in_6, %in_7 zp_lhs : %in_8 zp_rhs : %in_9 : i8, i8, i32, i32 -> i32
//CHECK-NEXT:      dart.yield %24 : i32
//CHECK-NEXT:    }) : (!dart.stream<i8>, !dart.stream<i8>, !dart.stream<i32>, !dart.stream<i32>) -> !dart.stream<i32>
//CHECK-NEXT:    dart.yield %23 : !dart.stream<i32>
//CHECK-NEXT:  }) : (tensor<16x16xi8>, tensor<16x16xi8>, i32, i32, tensor<16x16xi32>) -> tensor<16x16xi32>

%9 = tensor.empty() : tensor<16x16xi32>
%10 = arith.constant dense<5> : tensor<16xi32>
%11 = linalg.generic {indexing_maps = [affine_map<(d0, d1) -> (d1)>, affine_map<(d0, d1) -> (d0, d1)>], iterator_types = ["parallel", "parallel"]} ins(%10 : tensor<16xi32>) outs(%9 : tensor<16x16xi32>) {
^bb0(%arg3: i32, %arg4: i32):
  linalg.yield %arg3 : i32
} -> tensor<16x16xi32>

// CHECK-NEXT: %25 = tensor.empty() : tensor<16x16xi32>
// CHECK-NEXT: %26 = arith.constant dense<5> : tensor<16xi32>
// CHECK-NEXT: %27 = linalg.generic {indexing_maps = [affine_map<(d0, d1) -> (d1)>, affine_map<(d0, d1) -> (d0, d1)>], iterator_types = ["parallel", "parallel"]} ins(%26 : tensor<16xi32>) outs(%25 : tensor<16x16xi32>) {
// CHECK-NEXT: ^bb6(%arg3: i32, %arg4: i32):
// CHECK-NEXT:   linalg.yield %arg3 : i32
// CHECK-NEXT: } -> tensor<16x16xi32>

%12 = linalg.generic {indexing_maps = [affine_map<(d0, d1, d2) -> (d0, d2)>, affine_map<(d0, d1, d2) -> (d2, d1)>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> (d0, d1)>], iterator_types = ["parallel", "parallel", "reduction"], library_call = "snax_gemmx_stream"} ins(%arg0, %arg1, %c0_i32, %c0_i32 : tensor<16x16xi8>, tensor<16x16xi8>, i32, i32) outs(%11 : tensor<16x16xi32>) {
^bb0(%in_10: i8, %in_11: i8, %in_12: i32, %in_13: i32, %out_3: i32):
  %13 = kernel.qmac %in_10, %in_11 zp_lhs : %in_12 zp_rhs : %in_13 : i8, i8, i32, i32 -> i32
  linalg.yield %13 : i32
} -> tensor<16x16xi32>

// CHECK-NEXT: %28 = "dart.operation"(%arg0, %arg1, %c0_i32, %c0_i32, %27) <{patterns = [affine_map<(d0, d1, d2) -> (d0, d2)>, affine_map<(d0, d1, d2) -> (d2, d1)>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> ()>, affine_map<(d0, d1, d2) -> (d0, d1)>], accelerator = "snax_gemmx", operandSegmentSizes = array<i32: 4, 1>}> ({
// CHECK-NEXT: ^bb7(%29: !dart.stream<i8>, %30: !dart.stream<i8>, %31: !dart.stream<i32>, %32: !dart.stream<i32>, %33: !dart.stream<i32>):
// CHECK-NEXT:   %34 = "dart.generic"(%29, %30, %31, %32) <{library_call = "snax_gemmx"}> ({
// CHECK-NEXT:   ^bb8(%in_10: i8, %in_11: i8, %in_12: i32, %in_13: i32, %out_3: i32):
// CHECK-NEXT:     %35 = kernel.qmac %in_10, %in_11 zp_lhs : %in_12 zp_rhs : %in_13 : i8, i8, i32, i32 -> i32
// CHECK-NEXT:     dart.yield %35 : i32
// CHECK-NEXT:   }) : (!dart.stream<i8>, !dart.stream<i8>, !dart.stream<i32>, !dart.stream<i32>) -> !dart.stream<i32>
// CHECK-NEXT:   dart.yield %34 : !dart.stream<i32>
// CHECK-NEXT: }) : (tensor<16x16xi8>, tensor<16x16xi8>, i32, i32, tensor<16x16xi32>) -> tensor<16x16xi32>

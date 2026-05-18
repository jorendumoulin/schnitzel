// RUN: snax-opt %s -p phs-divf-to-reciprocal-bitcast | filecheck %s

builtin.module {

  // f32 divf is rewritten to mul-by-bitcast-reciprocal with one Newton iter.
  func.func @divf_f32(%a: f32, %b: f32) -> f32 {
    %r = arith.divf %a, %b : f32
    return %r : f32
  }

// CHECK-LABEL: func.func @divf_f32
// CHECK:       %[[BI:.*]] = arith.bitcast %{{.*}} : f32 to i32
// CHECK:       %[[MAGIC:.*]] = arith.constant 2129859011 : i32
// CHECK:       %[[S:.*]] = arith.subi %[[MAGIC]], %[[BI]] : i32
// CHECK:       %[[Y0:.*]] = arith.bitcast %[[S]] : i32 to f32
// CHECK:       %[[TWO:.*]] = arith.constant 2.000000e+00 : f32
// CHECK:       %[[BY:.*]] = arith.mulf %{{.*}}, %[[Y0]] : f32
// CHECK:       %[[NR:.*]] = arith.subf %[[TWO]], %[[BY]] : f32
// CHECK:       %[[Y1:.*]] = arith.mulf %[[Y0]], %[[NR]] : f32
// CHECK:       %[[R:.*]] = arith.mulf %{{.*}}, %[[Y1]] : f32
// CHECK:       return %[[R]] : f32

  // Non-f32 types are left alone (pass only rewrites f32 today).
  func.func @divf_f64(%a: f64, %b: f64) -> f64 {
    %r = arith.divf %a, %b : f64
    return %r : f64
  }

// CHECK-LABEL: func.func @divf_f64
// CHECK:       %[[R2:.*]] = arith.divf %{{.*}}, %{{.*}} : f64
// CHECK:       return %[[R2]] : f64

}

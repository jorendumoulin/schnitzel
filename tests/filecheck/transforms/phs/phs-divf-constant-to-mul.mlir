// RUN: snax-opt %s -p phs-divf-constant-to-mul | filecheck %s

builtin.module {

  // Constant rhs: divf rewritten to mulf by reciprocal.
  func.func @divf_by_const(%x: f32) -> f32 {
    %cst = arith.constant 1.250000e+02 : f32
    %r = arith.divf %x, %cst : f32
    return %r : f32
  }

// CHECK-LABEL: func.func @divf_by_const
// CHECK:       %[[CST:.*]] = arith.constant 1.250000e+02 : f32
// CHECK:       %[[RECIP:.*]] = arith.constant 8.000000e-03 : f32
// CHECK:       %[[R:.*]] = arith.mulf %{{.*}}, %[[RECIP]] : f32
// CHECK:       return %[[R]] : f32

  // Non-constant rhs: divf is left untouched (softmax normalizer pattern).
  func.func @divf_by_var(%num: f32, %den: f32) -> f32 {
    %r = arith.divf %num, %den : f32
    return %r : f32
  }

// CHECK-LABEL: func.func @divf_by_var
// CHECK:       %[[R2:.*]] = arith.divf %{{.*}}, %{{.*}} : f32
// CHECK:       return %[[R2]] : f32

  // Zero constant rhs: divf is left untouched (avoid producing inf reciprocal).
  func.func @divf_by_zero(%x: f32) -> f32 {
    %zero = arith.constant 0.000000e+00 : f32
    %r = arith.divf %x, %zero : f32
    return %r : f32
  }

// CHECK-LABEL: func.func @divf_by_zero
// CHECK:       %[[Z:.*]] = arith.constant 0.000000e+00 : f32
// CHECK:       %[[R3:.*]] = arith.divf %{{.*}}, %[[Z]] : f32
// CHECK:       return %[[R3]] : f32

}

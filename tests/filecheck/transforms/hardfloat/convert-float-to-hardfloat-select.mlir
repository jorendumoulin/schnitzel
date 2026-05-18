// RUN: snax-opt -p convert-float-to-hardfloat %s | filecheck %s

// `arith.select` on float operands gets sandwiched in unrealized casts so
// the inner select runs on the integer bit-encoding; circt-opt's
// --map-arith-to-comb only lowers integer-typed selects.
func.func @select_f32(%cond : i1, %a : f32, %b : f32) -> f32 {
  %r = arith.select %cond, %a, %b : f32
  return %r : f32
}

// CHECK-LABEL: @select_f32
// CHECK: %{{.*}} = builtin.unrealized_conversion_cast %{{.*}} : f32 to i32
// CHECK: %{{.*}} = builtin.unrealized_conversion_cast %{{.*}} : f32 to i32
// CHECK: arith.select {{.*}} : i32
// CHECK: builtin.unrealized_conversion_cast %{{.*}} : i32 to f32

// Integer-typed selects must be left alone.
func.func @select_i32(%cond : i1, %a : i32, %b : i32) -> i32 {
  %r = arith.select %cond, %a, %b : i32
  return %r : i32
}

// CHECK-LABEL: @select_i32
// CHECK-NOT: unrealized_conversion_cast
// CHECK: arith.select {{.*}} : i32

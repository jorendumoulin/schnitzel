// RUN: snax-opt -p convert-float-to-hardfloat %s | filecheck %s

// `arith.bitcast` between a float and a same-width integer is bit-pattern
// preserving, so it is retyped to `builtin.unrealized_conversion_cast` to
// give `reconcile_unrealized_casts` a chance to fold it against neighboring
// casts emitted by the hardfloat lowering. Same-class bitcasts (int->int)
// stay as-is.

func.func @bitcast_cross_kind(%a : f32, %b : i32) -> (i32, f32) {
  %0 = arith.bitcast %a : f32 to i32
  %1 = arith.bitcast %b : i32 to f32
  return %0, %1 : i32, f32
}

// CHECK-LABEL: @bitcast_cross_kind
// CHECK: builtin.unrealized_conversion_cast %a : f32 to i32
// CHECK: builtin.unrealized_conversion_cast %b : i32 to f32
// CHECK-NOT: arith.bitcast

func.func @bitcast_same_kind(%b : i32) -> i32 {
  %0 = arith.bitcast %b : i32 to i32
  return %0 : i32
}

// CHECK-LABEL: @bitcast_same_kind
// CHECK: arith.bitcast
// CHECK-NOT: unrealized_conversion_cast

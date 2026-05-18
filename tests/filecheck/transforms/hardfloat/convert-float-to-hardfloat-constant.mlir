// RUN: snax-opt -p convert-float-to-hardfloat %s | filecheck %s

// Float-typed `arith.constant` is rewritten to the matching integer
// bit-pattern + an unrealized cast back to the float type. Integer
// constants are left alone.
func.func @test_const() -> (f32, f64, i32) {
  %a = arith.constant 1.500000e+00 : f32
  %b = arith.constant 3.000000e+00 : f64
  %c = arith.constant 42 : i32
  return %a, %b, %c : f32, f64, i32
}

// CHECK-LABEL: @test_const
// CHECK: arith.constant 1069547520 : i32
// CHECK: builtin.unrealized_conversion_cast {{.*}} : i32 to f32
// CHECK: arith.constant 4613937818241073152 : i64
// CHECK: builtin.unrealized_conversion_cast {{.*}} : i64 to f64
// CHECK: arith.constant 42 : i32

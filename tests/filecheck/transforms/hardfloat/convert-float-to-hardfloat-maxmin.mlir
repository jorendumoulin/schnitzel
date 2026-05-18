// RUN: snax-opt -p convert-float-to-hardfloat %s | filecheck %s

func.func @test_max_min(%a: f32, %b: f32) -> (f32, f32) {
  %mx = arith.maximumf %a, %b : f32
  %mn = arith.minimumf %a, %b : f32
  return %mx, %mn : f32, f32
}

// Each op emits exactly one compare, one qNaN constant, two arith.select,
// and one tie-break (and/or). Max additionally inverts the sign bit.

// CHECK-LABEL: @test_max_min
// CHECK: hardfloat.compare_rec_fn<24, 8>
// CHECK: arith.cmpi slt
// CHECK: arith.xori
// CHECK: arith.andi
// CHECK: arith.ori
// CHECK: arith.select
// CHECK: hw.constant 2143289344 : i32
// CHECK: arith.select

// Minimumf — no xori (uses lhs_neg directly).
// CHECK: hardfloat.compare_rec_fn<24, 8>
// CHECK: arith.cmpi slt
// CHECK: arith.andi
// CHECK: arith.ori
// CHECK: arith.select
// CHECK: hw.constant 2143289344 : i32
// CHECK: arith.select

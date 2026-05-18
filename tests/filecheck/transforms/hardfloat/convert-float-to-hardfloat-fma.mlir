// RUN: snax-opt -p convert-float-to-hardfloat %s | filecheck %s

func.func @test_fma(%a: f32, %b: f32, %c: f32) -> f32 {
  %r = math.fma %a, %b, %c : f32
  return %r : f32
}

// CHECK-LABEL: @test_fma
// CHECK: hw.constant 0 : i2
// CHECK: hardfloat.mul_add_rec_fn<24, 8>

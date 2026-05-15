// RUN: snax-opt -p convert-float-to-hardfloat %s | filecheck %s

func.func @test_truncext(%a : f32, %b : f16) -> (f16, f32) {
  %tr = arith.truncf %a : f32 to f16
  %ex = arith.extf %b : f16 to f32
  return %tr, %ex : f16, f32
}

// CHECK-LABEL: @test_truncext
// truncf f32→f16: in_sig=24, in_exp=8, out_sig=11, out_exp=5
// CHECK: hardfloat.rec_fn_to_rec_fn<24, 8, 11, 5>
// extf  f16→f32: in_sig=11, in_exp=5, out_sig=24, out_exp=8
// CHECK: hardfloat.rec_fn_to_rec_fn<11, 5, 24, 8>

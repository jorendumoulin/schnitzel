// RUN: snax-opt -p convert-float-to-hardfloat %s | filecheck %s

// Integer<->float conversion should pick the bitwidths separately:
//   - integer port uses the integer's bitwidth (i8 here)
//   - recoded intermediate uses the float's bitwidth + 1 (i33 for f32)
//   - decoded float uses the float's bitwidth (i32 for f32)

func.func @sitofp_i8_f32(%a : i8) -> f32 {
  %r = arith.sitofp %a : i8 to f32
  return %r : f32
}

// CHECK-LABEL: @sitofp_i8_f32
// CHECK: hardfloat.in_to_rec_fn<24, 8, 8>{{.*}}: (i1, i8, i3, i1) -> (i33, i5)
// CHECK: hardfloat.rec_fn_to_fn<24, 8>{{.*}}: (i33) -> i32

func.func @fptosi_f32_i8(%a : f32) -> i8 {
  %r = arith.fptosi %a : f32 to i8
  return %r : i8
}

// CHECK-LABEL: @fptosi_f32_i8
// CHECK: hardfloat.fn_to_rec_fn<24, 8>{{.*}}: (i32) -> i33
// CHECK: hardfloat.rec_fn_to_in<24, 8, 8>{{.*}}: (i33, i3, i1) -> (i8, i3)

func.func @uitofp_i16_f32(%a : i16) -> f32 {
  %r = arith.uitofp %a : i16 to f32
  return %r : f32
}

// CHECK-LABEL: @uitofp_i16_f32
// CHECK: hardfloat.in_to_rec_fn<24, 8, 16>{{.*}}: (i1, i16, i3, i1) -> (i33, i5)
// CHECK: hardfloat.rec_fn_to_fn<24, 8>{{.*}}: (i33) -> i32

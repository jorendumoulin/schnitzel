// RUN: snax-opt -p convert-float-to-hardfloat %s | filecheck %s

// `math.roundeven %x : f32` is lowered as a float->int->float round-trip
// with rounding mode 0 (RNE), using the float bit-width as the intermediate
// integer width.
func.func @roundeven(%x : f32) -> f32 {
  %r = math.roundeven %x : f32
  return %r : f32
}

// CHECK-LABEL: @roundeven
// CHECK: builtin.unrealized_conversion_cast %x : f32 to i32
// CHECK: hardfloat.fn_to_rec_fn<24, 8>{{.*}}: (i32) -> i33
// CHECK: hardfloat.rec_fn_to_in<24, 8, 32>{{.*}}: (i33, i3, i1) -> (i32, i3)
// CHECK: hardfloat.in_to_rec_fn<24, 8, 32>{{.*}}: (i1, i32, i3, i1) -> (i33, i5)
// CHECK: hardfloat.rec_fn_to_fn<24, 8>{{.*}}: (i33) -> i32
// CHECK: builtin.unrealized_conversion_cast {{.*}} : i32 to f32

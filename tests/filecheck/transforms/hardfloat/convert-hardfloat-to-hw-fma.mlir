// REQUIRES: has_easyfloat_installed
// RUN: snax-opt -p convert-hardfloat-to-hw{'easyfloat_path="%p/../../../../../kuleuven-easyfloat"'} %s | filecheck %s
// RUN: snax-opt -p convert-hardfloat-to-hw{external_modules=true} %s | filecheck %s --check-prefix=EXTERN


func.func @test_fma(%a : f32, %b : f32, %c : f32) -> f32 {
  %rm = arith.constant 0 : i3
  %tininess = arith.constant true
  %op = arith.constant 0 : i2
  %a_i32 = builtin.unrealized_conversion_cast %a : f32 to i32
  %b_i32 = builtin.unrealized_conversion_cast %b : f32 to i32
  %c_i32 = builtin.unrealized_conversion_cast %c : f32 to i32
  %a_rec = hardfloat.fn_to_rec_fn<24, 8>(%a_i32) : (i32) -> i33
  %b_rec = hardfloat.fn_to_rec_fn<24, 8>(%b_i32) : (i32) -> i33
  %c_rec = hardfloat.fn_to_rec_fn<24, 8>(%c_i32) : (i32) -> i33
  %r_rec, %flags = hardfloat.mul_add_rec_fn<24, 8>(%op, %a_rec, %b_rec, %c_rec, %rm, %tininess) : (i2, i33, i33, i33, i3, i1) -> (i33, i5)
  %r_i32 = hardfloat.rec_fn_to_fn<24, 8>(%r_rec) : (i33) -> i32
  %r_f32 = builtin.unrealized_conversion_cast %r_i32 : i32 to f32
  func.return %r_f32 : f32
}

// CHECK: hw.instance "MulAddRecFN_s24_e8_0" @MulAddRecFN_s24_e8(io_op: %op: i2, io_a: %a_rec: i33, io_b: %b_rec: i33, io_c: %c_rec: i33, io_roundingMode: %rm: i3, io_detectTininess: %tininess: i1) -> (io_out: i33, io_exceptionFlags: i5)
// CHECK: hw.module private @MulAddRecFN_s24_e8(in %io_op: i2, in %io_a: i33, in %io_b: i33, in %io_c: i33, in %io_roundingMode: i3, in %io_detectTininess: i1, out io_out: i33, out io_exceptionFlags: i5) {

// EXTERN: hw.module.extern @MulAddRecFN_s24_e8(in %port0 io_op: i2, in %port1 io_a: i33, in %port2 io_b: i33, in %port3 io_c: i33, in %port4 io_roundingMode: i3, in %port5 io_detectTininess: i1, out io_out: i33, out io_exceptionFlags: i5)

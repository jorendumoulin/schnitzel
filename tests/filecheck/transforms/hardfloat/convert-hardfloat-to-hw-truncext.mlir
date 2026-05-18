// REQUIRES: has_easyfloat_installed
// RUN: snax-opt -p convert-hardfloat-to-hw{'easyfloat_path="%p/../../../../../kuleuven-easyfloat"'} %s | filecheck %s
// RUN: snax-opt -p convert-hardfloat-to-hw{external_modules=true} %s | filecheck %s --check-prefix=EXTERN


func.func @test_truncext(%a: f32) -> f16 {
  %rm = arith.constant 0 : i3
  %tininess = arith.constant true
  %a_i32 = builtin.unrealized_conversion_cast %a : f32 to i32
  %a_rec = hardfloat.fn_to_rec_fn<24, 8>(%a_i32) : (i32) -> i33
  %tr, %flags = hardfloat.rec_fn_to_rec_fn<24, 8, 11, 5>(%a_rec, %rm, %tininess) : (i33, i3, i1) -> (i17, i5)
  %tr_i16 = hardfloat.rec_fn_to_fn<11, 5>(%tr) : (i17) -> i16
  %tr_f16 = builtin.unrealized_conversion_cast %tr_i16 : i16 to f16
  func.return %tr_f16 : f16
}

// CHECK: hw.instance "RecFNToRecFN_is24_ie8_os11_oe5_0" @RecFNToRecFN_is24_ie8_os11_oe5(io_in: %a_rec: i33, io_roundingMode: %rm: i3, io_detectTininess: %tininess: i1) -> (io_out: i17, io_exceptionFlags: i5)
// CHECK: hw.module private @RecFNToRecFN_is24_ie8_os11_oe5(in %io_in: i33, in %io_roundingMode: i3, in %io_detectTininess: i1, out io_out: i17, out io_exceptionFlags: i5) {

// EXTERN: hw.module.extern @RecFNToRecFN_is24_ie8_os11_oe5(in %port0 io_in: i33, in %port1 io_roundingMode: i3, in %port2 io_detectTininess: i1, out io_out: i17, out io_exceptionFlags: i5)

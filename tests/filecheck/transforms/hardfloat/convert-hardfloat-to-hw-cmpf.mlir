// REQUIRES: has_easyfloat_installed
// RUN: snax-opt -p convert-hardfloat-to-hw{'easyfloat_path="%p/../../../../../kuleuven-easyfloat"'} %s | filecheck %s
// RUN: snax-opt -p convert-hardfloat-to-hw{external_modules=true} %s | filecheck %s --check-prefix=EXTERN


func.func @test_cmpf(%a : f32, %b : f32) -> i1 {
  %false = arith.constant false
  %a_i32 = builtin.unrealized_conversion_cast %a : f32 to i32
  %b_i32 = builtin.unrealized_conversion_cast %b : f32 to i32
  %a_rec = hardfloat.fn_to_rec_fn<24, 8>(%a_i32) : (i32) -> i33
  %b_rec = hardfloat.fn_to_rec_fn<24, 8>(%b_i32) : (i32) -> i33
  %lt, %eq, %gt, %flags = hardfloat.compare_rec_fn<24, 8>(%a_rec, %b_rec, %false) : (i33, i33, i1) -> (i1, i1, i1, i5)
  func.return %lt : i1
}

// CHECK: %lt, %eq, %gt, %flags = hw.instance "CompareRecFN_s24_e8_0" @CompareRecFN_s24_e8(io_a: %a_rec: i33, io_b: %b_rec: i33, io_signaling: %false: i1) -> (io_lt: i1, io_eq: i1, io_gt: i1, io_exceptionFlags: i5)
// CHECK: hw.module private @CompareRecFN_s24_e8(in %io_a: i33, in %io_b: i33, in %io_signaling: i1, out io_lt: i1, out io_eq: i1, out io_gt: i1, out io_exceptionFlags: i5) {

// EXTERN: hw.module.extern @CompareRecFN_s24_e8(in %port0 io_a: i33, in %port1 io_b: i33, in %port2 io_signaling: i1, out io_lt: i1, out io_eq: i1, out io_gt: i1, out io_exceptionFlags: i5)

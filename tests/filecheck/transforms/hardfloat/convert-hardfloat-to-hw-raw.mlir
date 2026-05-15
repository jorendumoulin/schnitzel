// REQUIRES: has_easyfloat_installed
// RUN: snax-opt -p convert-hardfloat-to-hw{'easyfloat_path="%p/../../../../../kuleuven-easyfloat"'} %s | filecheck %s
// RUN: snax-opt -p convert-hardfloat-to-hw{external_modules=true} %s | filecheck %s --check-prefix=EXTERN


// End-to-end HW lowering for the four new raw-bus ops. Confirms the Scala
// wrappers compile, the named modules emit with the `_s${sig}_e${exp}`
// suffix, and the bus widths line up with the dialect verifiers (i39 for
// the raw input bus, i41 for the raw output bus, i33 for recoded).

func.func @raw_add(%rec : i33, %rm : i3, %tn : i1, %sub : i1) -> i33 {
  %ra = hardfloat.recode_to_raw<24, 8>(%rec) : (i33) -> i39
  %inv, %raw = hardfloat.add_raw_fn<24, 8>(%sub, %ra, %ra) : (i1, i39, i39) -> (i1, i41)
  %out, %flags = hardfloat.round_raw_to_rec_fn<24, 8>(%inv, %raw, %rm, %tn) : (i1, i41, i3, i1) -> (i33, i5)
  func.return %out : i33
}

func.func @raw_mul(%rec : i33, %rm : i3, %tn : i1) -> i33 {
  %ra = hardfloat.recode_to_raw<24, 8>(%rec) : (i33) -> i39
  %inv, %raw = hardfloat.mul_raw_fn<24, 8>(%ra, %ra) : (i39, i39) -> (i1, i41)
  %out, %flags = hardfloat.round_raw_to_rec_fn<24, 8>(%inv, %raw, %rm, %tn) : (i1, i41, i3, i1) -> (i33, i5)
  func.return %out : i33
}

// CHECK-LABEL: @raw_add
// CHECK: hw.instance "RecFNToRawFNBus_s24_e8_0" @RecFNToRawFNBus_s24_e8(io_in: %rec: i33) -> (io_out: i39)
// CHECK: hw.instance "AddRawFNBus_s24_e8_0" @AddRawFNBus_s24_e8(io_subOp: %sub: i1, io_a: %ra: i39, io_b: %ra: i39) -> (io_invalidExc: i1, io_rawOut: i41)
// CHECK: hw.instance "RoundRawFNToRecFNBus_s24_e8_0" @RoundRawFNToRecFNBus_s24_e8(io_invalidExc: %inv: i1, io_in: %raw: i41, io_roundingMode: %rm: i3, io_detectTininess: %tn: i1) -> (io_out: i33, io_exceptionFlags: i5)

// CHECK-LABEL: @raw_mul
// CHECK: hw.instance "RecFNToRawFNBus_s24_e8_1" @RecFNToRawFNBus_s24_e8(io_in: %rec: i33) -> (io_out: i39)
// CHECK: hw.instance "MulRawFNBus_s24_e8_0" @MulRawFNBus_s24_e8(io_a: %ra: i39, io_b: %ra: i39) -> (io_invalidExc: i1, io_rawOut: i41)
// CHECK: hw.instance "RoundRawFNToRecFNBus_s24_e8_1" @RoundRawFNToRecFNBus_s24_e8(io_invalidExc: %inv: i1, io_in: %raw: i41, io_roundingMode: %rm: i3, io_detectTininess: %tn: i1) -> (io_out: i33, io_exceptionFlags: i5)

// All four hw.module bodies should appear in the inlined output (DAG —
// firtool interleaves internal Berkeley modules between ours).
// CHECK-DAG: hw.module private @RecFNToRawFNBus_s24_e8
// CHECK-DAG: hw.module private @AddRawFNBus_s24_e8
// CHECK-DAG: hw.module private @MulRawFNBus_s24_e8
// CHECK-DAG: hw.module private @RoundRawFNToRecFNBus_s24_e8

// External-only mode declares each as `hw.module.extern`.
// EXTERN: hw.module.extern @AddRawFNBus_s24_e8(in %port0 io_subOp: i1, in %port1 io_a: i39, in %port2 io_b: i39, out io_invalidExc: i1, out io_rawOut: i41)
// EXTERN-NEXT: hw.module.extern @MulRawFNBus_s24_e8(in %port0 io_a: i39, in %port1 io_b: i39, out io_invalidExc: i1, out io_rawOut: i41)
// EXTERN-NEXT: hw.module.extern @RecFNToRawFNBus_s24_e8(in %port0 io_in: i33, out io_out: i39)
// EXTERN-NEXT: hw.module.extern @RoundRawFNToRecFNBus_s24_e8(in %port0 io_invalidExc: i1, in %port1 io_in: i41, in %port2 io_roundingMode: i3, in %port3 io_detectTininess: i1, out io_out: i33, out io_exceptionFlags: i5)

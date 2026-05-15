// RUN: snax-opt -p cse %s | filecheck %s
// RUN: snax-opt -p convert-float-to-hardfloat,cse %s | filecheck %s --check-prefix=LOWERED

// After FinalizePhsToHWPass inlines per-region hardfloat ops into the parent
// block, identical pure ops on identical operands collapse via xDSL's CSE
// pass. This file simulates that post-finalize shape directly.

func.func @dedupe_compares(%a : i33, %b : i33) -> (i1, i1) {
  %false = arith.constant false
  %lt0, %eq0, %gt0, %f0 = hardfloat.compare_rec_fn<24, 8>(%a, %b, %false) : (i33, i33, i1) -> (i1, i1, i1, i5)
  %lt1, %eq1, %gt1, %f1 = hardfloat.compare_rec_fn<24, 8>(%a, %b, %false) : (i33, i33, i1) -> (i1, i1, i1, i5)
  func.return %lt0, %lt1 : i1, i1
}

// Only one compare_rec_fn survives; the second %lt becomes the first %lt.
// CHECK-LABEL: @dedupe_compares
// CHECK: hardfloat.compare_rec_fn<24, 8>
// CHECK-NOT: hardfloat.compare_rec_fn<24, 8>
// CHECK: func.return


// Recode pairs collapse alongside their consumers.
func.func @dedupe_recodes(%a : f32, %b : f32) -> (f32, f32) {
  %add0 = arith.addf %a, %b : f32
  %add1 = arith.addf %a, %b : f32
  func.return %add0, %add1 : f32, f32
}

// First run uses `cse` alone: arith.addf has no CSE candidates yet.
// CHECK-LABEL: @dedupe_recodes
// CHECK: arith.addf
// CHECK-NOT: arith.addf
// CHECK: func.return

// Second run lowers to hardfloat first, then CSE collapses everything.
// LOWERED-LABEL: @dedupe_recodes
// LOWERED: hardfloat.fn_to_rec_fn<24, 8>
// LOWERED: hardfloat.fn_to_rec_fn<24, 8>
// LOWERED-NOT: hardfloat.fn_to_rec_fn<24, 8>
// LOWERED: hardfloat.add_rec_fn<24, 8>
// LOWERED-NOT: hardfloat.add_rec_fn<24, 8>
// LOWERED: hardfloat.rec_fn_to_fn<24, 8>
// LOWERED-NOT: hardfloat.rec_fn_to_fn<24, 8>

// RUN: snax-opt -p convert-float-to-hardfloat %s | filecheck %s

func.func @cmpf_ord_unord(%a: f32, %b: f32) -> (i1, i1, i1, i1, i1, i1, i1, i1) {
  // Constant predicates
  %t = arith.cmpf true, %a, %b : f32
  %f = arith.cmpf false, %a, %b : f32
  // Ordered family
  %oeq = arith.cmpf oeq, %a, %b : f32
  %olt = arith.cmpf olt, %a, %b : f32
  %ord = arith.cmpf ord, %a, %b : f32
  // Unordered family
  %ueq = arith.cmpf ueq, %a, %b : f32
  %une = arith.cmpf une, %a, %b : f32
  %uno = arith.cmpf uno, %a, %b : f32
  return %t, %f, %oeq, %olt, %ord, %ueq, %une, %uno : i1, i1, i1, i1, i1, i1, i1, i1
}

// `true` and `false` collapse to a single hw.constant, no compare emitted.
// CHECK-LABEL: @cmpf_ord_unord
// CHECK: hw.constant true
// CHECK: hw.constant false

// Every other case emits exactly one compare per pair (a, b).
// CHECK: hardfloat.compare_rec_fn<24, 8>
// CHECK: hardfloat.compare_rec_fn<24, 8>
// CHECK: hardfloat.compare_rec_fn<24, 8>
// CHECK: hardfloat.compare_rec_fn<24, 8>
// CHECK: hardfloat.compare_rec_fn<24, 8>
// CHECK: hardfloat.compare_rec_fn<24, 8>

// Spot-check predicate boolean wiring.
// oeq → eq result directly (no extra or/xor for the result selection itself)
// uno → XOR of ord with const 1
// CHECK: arith.xori

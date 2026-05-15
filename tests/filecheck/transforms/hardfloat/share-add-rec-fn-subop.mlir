// RUN: snax-opt -p share-add-rec-fn-subop %s | filecheck %s

// addf in lane 0 (subOp = false) and subf in lane 1 (subOp = true) on the
// same operands collapse into a single shared `add_rec_fn` whose subOp is
// muxed by the same switch the original array_get used.
func.func @share_addf_subf(%a : i33, %b : i33, %sw : i1) -> i33 {
  %false = arith.constant false
  %true = arith.constant true
  %rm = arith.constant 0 : i3
  %add, %fa = hardfloat.add_rec_fn<24, 8>(%false, %a, %b, %rm, %false) : (i1, i33, i33, i3, i1) -> (i33, i5)
  %sub, %fb = hardfloat.add_rec_fn<24, 8>(%true,  %a, %b, %rm, %false) : (i1, i33, i33, i3, i1) -> (i33, i5)
  %arr = hw.array_create %add, %sub : i33
  %out = hw.array_get %arr[%sw] : !hw.array<2xi33>, i1
  func.return %out : i33
}

// CHECK-LABEL: @share_addf_subf
// subOp values muxed by the same switch.
// CHECK: hw.array_create %false, %true : i1
// CHECK: %[[SUBOP:.+]] = hw.array_get
// One shared add_rec_fn consuming the muxed subOp.
// CHECK: %[[SHARED:.+]], %{{.+}} = hardfloat.add_rec_fn<24, 8>(%[[SUBOP]], %a, %b, %rm, %false)
// CHECK-NOT: hardfloat.add_rec_fn
// Replaces the array_get's use site directly.
// CHECK: func.return %[[SHARED]] : i33


// Three-lane case: two addfs (one with each constant) and one subf. The
// pass still fires — even though there's a third lane with same subOp as
// the first, we just need every other operand to match.
func.func @share_three_lanes(%a : i33, %b : i33, %sw : i2) -> i33 {
  %false = arith.constant false
  %true = arith.constant true
  %rm = arith.constant 0 : i3
  %add0, %f0 = hardfloat.add_rec_fn<24, 8>(%false, %a, %b, %rm, %false) : (i1, i33, i33, i3, i1) -> (i33, i5)
  %sub,  %f1 = hardfloat.add_rec_fn<24, 8>(%true,  %a, %b, %rm, %false) : (i1, i33, i33, i3, i1) -> (i33, i5)
  %add1, %f2 = hardfloat.add_rec_fn<24, 8>(%false, %a, %b, %rm, %false) : (i1, i33, i33, i3, i1) -> (i33, i5)
  %arr = hw.array_create %add0, %sub, %add1 : i33
  %out = hw.array_get %arr[%sw] : !hw.array<3xi33>, i2
  func.return %out : i33
}

// CHECK-LABEL: @share_three_lanes
// CHECK: hw.array_create %false, %true, %false : i1
// CHECK: hw.array_get
// CHECK: %[[SHARED3:.+]], %{{.+}} = hardfloat.add_rec_fn<24, 8>
// CHECK-NOT: hardfloat.add_rec_fn
// CHECK: func.return %[[SHARED3]]


// Negative case: lanes operate on different `%a` operands, so the pass
// can't safely share a single block. Leave the structure alone.
func.func @different_operands_no_share(%a : i33, %b : i33, %c : i33, %sw : i1) -> i33 {
  %false = arith.constant false
  %rm = arith.constant 0 : i3
  %ab, %fa = hardfloat.add_rec_fn<24, 8>(%false, %a, %b, %rm, %false) : (i1, i33, i33, i3, i1) -> (i33, i5)
  %cb, %fc = hardfloat.add_rec_fn<24, 8>(%false, %c, %b, %rm, %false) : (i1, i33, i33, i3, i1) -> (i33, i5)
  %arr = hw.array_create %ab, %cb : i33
  %out = hw.array_get %arr[%sw] : !hw.array<2xi33>, i1
  func.return %out : i33
}

// CHECK-LABEL: @different_operands_no_share
// Two original add_rec_fn ops still present.
// CHECK: hardfloat.add_rec_fn<24, 8>(%false, %a, %b
// CHECK: hardfloat.add_rec_fn<24, 8>(%false, %c, %b
// CHECK: hw.array_create
// CHECK: hw.array_get

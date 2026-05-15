// RUN: snax-opt -p merge-across-array-get %s | filecheck %s

// ---------------------------------------------------------------------------
// Flavor 1: sink rounder past array_get — fully shared (every lane is a
// rounder, all from the same (sig, exp, rm, tn) bucket).
// ---------------------------------------------------------------------------
func.func @two_rounders_shared(%inv0 : i1, %raw0 : i41, %inv1 : i1, %raw1 : i41, %sw : i1) -> i33 {
  %rm = arith.constant 0 : i3
  %tn = arith.constant true
  %r0, %f0 = hardfloat.round_raw_to_rec_fn<24, 8>(%inv0, %raw0, %rm, %tn) : (i1, i41, i3, i1) -> (i33, i5)
  %r1, %f1 = hardfloat.round_raw_to_rec_fn<24, 8>(%inv1, %raw1, %rm, %tn) : (i1, i41, i3, i1) -> (i33, i5)
  %arr = hw.array_create %r0, %r1 : i33
  %out = hw.array_get %arr[%sw] : !hw.array<2xi33>, i1
  func.return %out : i33
}

// CHECK-LABEL: @two_rounders_shared
// CHECK: hw.array_create %inv0, %inv1 : i1
// CHECK: hw.array_create %raw0, %raw1 : i41
// CHECK: hw.array_get
// CHECK: hw.array_get
// CHECK: %[[SHARED:.+]], %{{.+}} = hardfloat.round_raw_to_rec_fn<24, 8>
// CHECK-NOT: hardfloat.round_raw_to_rec_fn
// CHECK: func.return %[[SHARED]] : i33


// ---------------------------------------------------------------------------
// Flavor 2: partial rounder sharing — lane 1 is a non-rounder pass-through.
// ---------------------------------------------------------------------------
func.func @partial_share_three_lanes(
    %inv0 : i1, %raw0 : i41,
    %inv1 : i1, %raw1 : i41,
    %other : i33,
    %sw : i2) -> i33 {
  %rm = arith.constant 0 : i3
  %tn = arith.constant true
  %r0, %f0 = hardfloat.round_raw_to_rec_fn<24, 8>(%inv0, %raw0, %rm, %tn) : (i1, i41, i3, i1) -> (i33, i5)
  %r1, %f1 = hardfloat.round_raw_to_rec_fn<24, 8>(%inv1, %raw1, %rm, %tn) : (i1, i41, i3, i1) -> (i33, i5)
  %arr = hw.array_create %r0, %other, %r1 : i33
  %out = hw.array_get %arr[%sw] : !hw.array<3xi33>, i2
  func.return %out : i33
}

// CHECK-LABEL: @partial_share_three_lanes
// CHECK: hw.array_create %inv0, %inv0, %inv1 : i1
// CHECK: hw.array_create %raw0, %raw0, %raw1 : i41
// CHECK: hw.array_get
// CHECK: hw.array_get
// CHECK: %[[SHARED:.+]], %{{.+}} = hardfloat.round_raw_to_rec_fn<24, 8>
// CHECK-NOT: hardfloat.round_raw_to_rec_fn
// CHECK: hw.array_create %[[SHARED]], %other, %[[SHARED]] : i33
// CHECK: hw.array_get


// ---------------------------------------------------------------------------
// Flavor 3: two independent rounder buckets in one array — each collapses
// to its own shared rounder, output dispatched by a result-array.
// ---------------------------------------------------------------------------
func.func @two_groups_two_lanes(
    %inv0 : i1, %raw0 : i41,
    %inv1 : i1, %raw1 : i41,
    %inv2 : i1, %raw2 : i41,
    %inv3 : i1, %raw3 : i41,
    %rm_a : i3, %tn_a : i1,
    %rm_b : i3, %tn_b : i1,
    %sw : i2) -> i33 {
  %ra0, %fa0 = hardfloat.round_raw_to_rec_fn<24, 8>(%inv0, %raw0, %rm_a, %tn_a) : (i1, i41, i3, i1) -> (i33, i5)
  %rb0, %fb0 = hardfloat.round_raw_to_rec_fn<24, 8>(%inv1, %raw1, %rm_b, %tn_b) : (i1, i41, i3, i1) -> (i33, i5)
  %ra1, %fa1 = hardfloat.round_raw_to_rec_fn<24, 8>(%inv2, %raw2, %rm_a, %tn_a) : (i1, i41, i3, i1) -> (i33, i5)
  %rb1, %fb1 = hardfloat.round_raw_to_rec_fn<24, 8>(%inv3, %raw3, %rm_b, %tn_b) : (i1, i41, i3, i1) -> (i33, i5)
  %arr = hw.array_create %ra0, %rb0, %ra1, %rb1 : i33
  %out = hw.array_get %arr[%sw] : !hw.array<4xi33>, i2
  func.return %out : i33
}

// CHECK-LABEL: @two_groups_two_lanes
// CHECK: hw.array_create %inv0, %inv0, %inv2, %inv0 : i1
// CHECK: hw.array_create %raw0, %raw0, %raw2, %raw0 : i41
// CHECK: hw.array_get
// CHECK: hw.array_get
// CHECK: %[[SHARED_A:.+]], %{{.+}} = hardfloat.round_raw_to_rec_fn<24, 8>({{.+}}, %rm_a, %tn_a)
// CHECK: hw.array_create %inv1, %inv1, %inv1, %inv3 : i1
// CHECK: hw.array_create %raw1, %raw1, %raw1, %raw3 : i41
// CHECK: hw.array_get
// CHECK: hw.array_get
// CHECK: %[[SHARED_B:.+]], %{{.+}} = hardfloat.round_raw_to_rec_fn<24, 8>({{.+}}, %rm_b, %tn_b)
// CHECK-NOT: hardfloat.round_raw_to_rec_fn
// CHECK: hw.array_create %[[SHARED_A]], %[[SHARED_B]], %[[SHARED_A]], %[[SHARED_B]] : i33
// CHECK: hw.array_get


// ---------------------------------------------------------------------------
// Flavor 4: addf vs subf — AddRecFnOp with muxed subOp.
// ---------------------------------------------------------------------------
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
// CHECK: hw.array_create %false, %true : i1
// CHECK: %[[SUBOP:.+]] = hw.array_get
// CHECK: %[[SHARED:.+]], %{{.+}} = hardfloat.add_rec_fn<24, 8>(%[[SUBOP]], %a, %b, %rm, %false)
// CHECK-NOT: hardfloat.add_rec_fn
// CHECK: func.return %[[SHARED]] : i33


// ---------------------------------------------------------------------------
// Flavor 5: sitofp vs uitofp — InToRecFnOp with muxed signedIn.
// ---------------------------------------------------------------------------
func.func @share_sitofp_uitofp(%i : i32, %sw : i1) -> i33 {
  %false = arith.constant false
  %true = arith.constant true
  %rm = arith.constant 0 : i3
  %sx, %fs = hardfloat.in_to_rec_fn<24, 8, 32>(%true,  %i, %rm, %false) : (i1, i32, i3, i1) -> (i33, i5)
  %ux, %fu = hardfloat.in_to_rec_fn<24, 8, 32>(%false, %i, %rm, %false) : (i1, i32, i3, i1) -> (i33, i5)
  %arr = hw.array_create %sx, %ux : i33
  %out = hw.array_get %arr[%sw] : !hw.array<2xi33>, i1
  func.return %out : i33
}

// CHECK-LABEL: @share_sitofp_uitofp
// CHECK: hw.array_create %true, %false : i1
// CHECK: %[[SIGNED:.+]] = hw.array_get
// CHECK: %[[SHARED:.+]], %{{.+}} = hardfloat.in_to_rec_fn<24, 8, 32>(%[[SIGNED]], %i, %rm, %false)
// CHECK-NOT: hardfloat.in_to_rec_fn
// CHECK: func.return %[[SHARED]] : i33


// ---------------------------------------------------------------------------
// Flavor 6: fptosi vs fptoui — RecFnToInOp with muxed signedOut.
// ---------------------------------------------------------------------------
func.func @share_fptosi_fptoui(%f : i33, %sw : i1) -> i32 {
  %false = arith.constant false
  %true = arith.constant true
  %rm = arith.constant 0 : i3
  %si, %fi0 = hardfloat.rec_fn_to_in<24, 8, 32>(%f, %rm, %true)  : (i33, i3, i1) -> (i32, i3)
  %ui, %fi1 = hardfloat.rec_fn_to_in<24, 8, 32>(%f, %rm, %false) : (i33, i3, i1) -> (i32, i3)
  %arr = hw.array_create %si, %ui : i32
  %out = hw.array_get %arr[%sw] : !hw.array<2xi32>, i1
  func.return %out : i32
}

// CHECK-LABEL: @share_fptosi_fptoui
// CHECK: hw.array_create %true, %false : i1
// CHECK: %[[SIGNED:.+]] = hw.array_get
// CHECK: %[[SHARED:.+]], %{{.+}} = hardfloat.rec_fn_to_in<24, 8, 32>(%f, %rm, %[[SIGNED]])
// CHECK-NOT: hardfloat.rec_fn_to_in
// CHECK: func.return %[[SHARED]] : i32


// ---------------------------------------------------------------------------
// Negative: lanes with different non-muxable operands stay untouched.
// ---------------------------------------------------------------------------
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
// CHECK: hardfloat.add_rec_fn<24, 8>(%false, %a, %b
// CHECK: hardfloat.add_rec_fn<24, 8>(%false, %c, %b
// CHECK: hw.array_create
// CHECK: hw.array_get

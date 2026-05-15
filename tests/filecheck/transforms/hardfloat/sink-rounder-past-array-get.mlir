// RUN: snax-opt -p sink-rounder-past-array-get %s | filecheck %s
// RUN: snax-opt -p sink-rounder-past-array-get,cse %s | filecheck %s --check-prefix=CSE

// Post-finalize shape: a per-region rounder feeds an array_create; the
// array_get picks one rounded value via the switch. The sink pass moves
// the rounder past the array_get so we end up with one rounder on muxed
// raw inputs.
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
// Two NEW array_creates appear (one for invalidExc, one for raw bus).
// CHECK: hw.array_create %inv0, %inv1 : i1
// CHECK: hw.array_create %raw0, %raw1 : i41
// CHECK: hw.array_get
// CHECK: hw.array_get
// Single shared rounder; both lanes are rounders so its output is the
// function return directly (no result-array rebuild).
// CHECK: %[[SHARED:.+]], %{{.+}} = hardfloat.round_raw_to_rec_fn<24, 8>
// CHECK-NOT: hardfloat.round_raw_to_rec_fn
// CHECK: func.return %[[SHARED]] : i33

// With CSE the two old per-region rounders disappear (their result feeds
// the original array_create, which is dead after the sink).
// CSE-LABEL: @two_rounders_shared
// CSE: hardfloat.round_raw_to_rec_fn<24, 8>
// CSE-NOT: hardfloat.round_raw_to_rec_fn
// CSE-LABEL: @mixed_array_no_sink


// Negative test: only one rounder in the array — nothing to share, the pass
// leaves the structure alone.
func.func @mixed_array_no_sink(%inv : i1, %raw : i41, %other : i33, %sw : i1) -> i33 {
  %rm = arith.constant 0 : i3
  %tn = arith.constant true
  %r0, %f0 = hardfloat.round_raw_to_rec_fn<24, 8>(%inv, %raw, %rm, %tn) : (i1, i41, i3, i1) -> (i33, i5)
  %arr = hw.array_create %r0, %other : i33
  %out = hw.array_get %arr[%sw] : !hw.array<2xi33>, i1
  func.return %out : i33
}

// CHECK-LABEL: @mixed_array_no_sink
// Single rounder + single array_create + single array_get survives untouched.
// CHECK: hardfloat.round_raw_to_rec_fn<24, 8>
// CHECK: hw.array_create
// CHECK: hw.array_get
// CHECK-NOT: hardfloat.round_raw_to_rec_fn
// CHECK-NOT: hw.array_create


// Partial sharing: two rounder lanes and one non-rounder lane in a 3-element
// array. The rounders merge into one shared rounder fed by muxed inv/raw
// buses; a result-array picks between the shared rounder result and the
// non-rounder lane value via the original switch.
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
// Two mux arrays (inv + raw) of length 3. Lane 1 (the non-rounder slot)
// gets `head.inv` / `head.raw` as don't-care fill — which is %inv0 / %raw0
// since the first rounder is the head.
// CHECK: hw.array_create %inv0, %inv0, %inv1 : i1
// CHECK: hw.array_create %raw0, %raw0, %raw1 : i41
// CHECK: hw.array_get
// CHECK: hw.array_get
// Single shared rounder.
// CHECK: %[[SHARED:.+]], %{{.+}} = hardfloat.round_raw_to_rec_fn<24, 8>
// CHECK-NOT: hardfloat.round_raw_to_rec_fn
// Result-array places the shared rounder result at the rounder lanes (0 and 2)
// and the original non-rounder value at lane 1.
// CHECK: hw.array_create %[[SHARED]], %other, %[[SHARED]] : i33
// CHECK: hw.array_get


// Two independent groups of rounders in one array_create: lanes 0,2 share
// `%rm_a`/`%tn_a`; lanes 1,3 share `%rm_b`/`%tn_b`. Each group of 2 collapses
// into one shared rounder, so the array_get is fed by a result-array picking
// between two shared rounders' outputs based on the switch.
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
// Group A (rm_a/tn_a) — lanes 0 and 2 share. Mux arrays use
// head=%inv0/%raw0; lane 1 and 3 are don't-care fills (also %inv0/%raw0).
// CHECK: hw.array_create %inv0, %inv0, %inv2, %inv0 : i1
// CHECK: hw.array_create %raw0, %raw0, %raw2, %raw0 : i41
// CHECK: hw.array_get
// CHECK: hw.array_get
// CHECK: %[[SHARED_A:.+]], %{{.+}} = hardfloat.round_raw_to_rec_fn<24, 8>({{.+}}, %rm_a, %tn_a)
//
// Group B (rm_b/tn_b) — lanes 1 and 3. Don't-care fill is %inv1/%raw1.
// CHECK: hw.array_create %inv1, %inv1, %inv1, %inv3 : i1
// CHECK: hw.array_create %raw1, %raw1, %raw1, %raw3 : i41
// CHECK: hw.array_get
// CHECK: hw.array_get
// CHECK: %[[SHARED_B:.+]], %{{.+}} = hardfloat.round_raw_to_rec_fn<24, 8>({{.+}}, %rm_b, %tn_b)
// CHECK-NOT: hardfloat.round_raw_to_rec_fn
//
// Result-array dispatches each lane to its group's shared rounder.
// CHECK: hw.array_create %[[SHARED_A]], %[[SHARED_B]], %[[SHARED_A]], %[[SHARED_B]] : i33
// CHECK: hw.array_get

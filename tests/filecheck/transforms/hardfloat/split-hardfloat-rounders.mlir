// RUN: snax-opt -p split-hardfloat-rounders %s | filecheck %s
// RUN: snax-opt -p split-hardfloat-rounders,cse %s | filecheck %s --check-prefix=CSE

func.func @split_add(%a : i33, %b : i33) -> i33 {
  %false = arith.constant false
  %rm = arith.constant 0 : i3
  %res, %flags = hardfloat.add_rec_fn<24, 8>(%false, %a, %b, %rm, %false) : (i1, i33, i33, i3, i1) -> (i33, i5)
  func.return %res : i33
}

// add_rec_fn becomes recode_to_raw × 2 + add_raw_fn + round_raw_to_rec_fn.
// CHECK-LABEL: @split_add
// CHECK: hardfloat.recode_to_raw<24, 8>
// CHECK: hardfloat.recode_to_raw<24, 8>
// CHECK: hardfloat.add_raw_fn<24, 8>
// CHECK: hardfloat.round_raw_to_rec_fn<24, 8>
// CHECK-NOT: hardfloat.add_rec_fn


func.func @split_mul(%a : i33, %b : i33) -> i33 {
  %rm = arith.constant 0 : i3
  %tn = arith.constant true
  %res, %flags = hardfloat.mul_rec_fn<24, 8>(%a, %b, %rm, %tn) : (i33, i33, i3, i1) -> (i33, i5)
  func.return %res : i33
}

// mul_rec_fn becomes recode_to_raw × 2 + mul_raw_fn + round_raw_to_rec_fn.
// CHECK-LABEL: @split_mul
// CHECK: hardfloat.recode_to_raw<24, 8>
// CHECK: hardfloat.recode_to_raw<24, 8>
// CHECK: hardfloat.mul_raw_fn<24, 8>
// CHECK: hardfloat.round_raw_to_rec_fn<24, 8>
// CHECK-NOT: hardfloat.mul_rec_fn


// Cross-core rounder sharing: addf and mulf on the same recoded operands
// with the same rounding mode + tininess produce identical
// `round_raw_to_rec_fn` ops after the split. CSE collapses them to one.
func.func @share_rounder_across_cores(%a : i33, %b : i33) -> (i33, i33) {
  %false = arith.constant false
  %rm = arith.constant 0 : i3
  %add_res, %add_flags = hardfloat.add_rec_fn<24, 8>(%false, %a, %b, %rm, %false) : (i1, i33, i33, i3, i1) -> (i33, i5)
  %mul_res, %mul_flags = hardfloat.mul_rec_fn<24, 8>(%a, %b, %rm, %false) : (i33, i33, i3, i1) -> (i33, i5)
  func.return %add_res, %mul_res : i33, i33
}

// Pre-dedup: 2 recodes per input. After CSE the two pairs collapse to 2 total
// (one per unique input SSA value). 1 add_raw_fn, 1 mul_raw_fn, and 2
// rounders survive because their inputs differ — sharing a rounder across
// heterogeneous cores requires muxing the raw outputs first, which is what
// FinalizePhsToHWPass does for ops in `phs.choose` regions. In this
// purely sequential example we just confirm the split form is well-typed
// and recode dedup works.
// CSE-LABEL: @share_rounder_across_cores
// CSE: hardfloat.recode_to_raw<24, 8>
// CSE: hardfloat.recode_to_raw<24, 8>
// CSE-NOT: hardfloat.recode_to_raw<24, 8>
// CSE: hardfloat.add_raw_fn<24, 8>
// CSE: hardfloat.round_raw_to_rec_fn<24, 8>
// CSE: hardfloat.mul_raw_fn<24, 8>
// CSE: hardfloat.round_raw_to_rec_fn<24, 8>

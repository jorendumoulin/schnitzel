// RUN: snax-opt %s --verify-diagnostics --split-input-file | filecheck %s

// Verifier rejects pe_array with more input maps in a mode than the
// referenced PE has data operands.

phs.pe @myacc (%0: i32, %1: i32) {
  %2 = arith.muli %0, %1 : i32
  phs.yield %2 : i32
}

// CHECK: input maps exceed PE data operand count
phs.pe_array @bad_inputs targets @myacc(%0: !hw.array<4xi32>, %1: !hw.array<4xi32>) -> (i32) attributes {bounds = array<i64: 4>, num_pure_inputs = 2 : i64, paired_outputs = array<i64>, input_modes = [[affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>]], output_modes = [[affine_map<(d0) -> (d0)>]]} {
  %2 = arith.constant 0 : i2
  %3 = hw.array_get %0[%2] : !hw.array<4xi32>, i2
  %4 = hw.array_get %1[%2] : !hw.array<4xi32>, i2
  %5 = phs.instance "pe_0" @myacc(%3, %4 : i32, i32) -> i32
  phs.yield %5 : i32
}

// -----

phs.pe @myacc (%0: i32, %1: i32) {
  %2 = arith.muli %0, %1 : i32
  phs.yield %2 : i32
}

// CHECK: PEArrayOp input_modes/output_modes length mismatch
phs.pe_array @bad_mode_count targets @myacc(%0: !hw.array<4xi32>, %1: !hw.array<4xi32>) -> (i32) attributes {bounds = array<i64: 4>, num_pure_inputs = 2 : i64, paired_outputs = array<i64>, input_modes = [[affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>], [affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>]], output_modes = [[affine_map<(d0) -> (d0)>]]} {
  %2 = arith.constant 0 : i2
  %3 = hw.array_get %0[%2] : !hw.array<4xi32>, i2
  %4 = hw.array_get %1[%2] : !hw.array<4xi32>, i2
  %5 = phs.instance "pe_0" @myacc(%3, %4 : i32, i32) -> i32
  phs.yield %5 : i32
}

// -----

// PE has no switches but instance tries to pass one.

phs.pe @noswitch_pe (%0: i32, %1: i32) {
  %2 = arith.muli %0, %1 : i32
  phs.yield %2 : i32
}

// CHECK: phs.instance: 1 switches but PE @noswitch_pe expects 0
phs.pe_array @bad_switch_count targets @noswitch_pe with %sw (%0: !hw.array<4xi32>, %1: !hw.array<4xi32>) -> (i32) attributes {bounds = array<i64: 4>, num_pure_inputs = 2 : i64, paired_outputs = array<i64>, input_modes = [[affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>]], output_modes = [[affine_map<(d0) -> (d0)>]]} {
  %2 = arith.constant 0 : i2
  %3 = hw.array_get %0[%2] : !hw.array<4xi32>, i2
  %4 = hw.array_get %1[%2] : !hw.array<4xi32>, i2
  %5 = phs.instance "pe_0" @noswitch_pe(%3, %4 : i32, i32) switches(%sw : index) -> i32
  phs.yield %5 : i32
}

// -----

// Instance data operand type mismatch.

phs.pe @i32_pe (%0: i32, %1: i32) {
  %2 = arith.muli %0, %1 : i32
  phs.yield %2 : i32
}

// CHECK: phs.instance data operand 0 type i64 != PE @i32_pe data operand type i32
phs.pe_array @bad_op_type targets @i32_pe(%0: !hw.array<4xi64>, %1: !hw.array<4xi32>) -> (i32) attributes {bounds = array<i64: 4>, num_pure_inputs = 2 : i64, paired_outputs = array<i64>, input_modes = [[affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>]], output_modes = [[affine_map<(d0) -> (d0)>]]} {
  %2 = arith.constant 0 : i2
  %3 = hw.array_get %0[%2] : !hw.array<4xi64>, i2
  %4 = hw.array_get %1[%2] : !hw.array<4xi32>, i2
  %5 = phs.instance "pe_0" @i32_pe(%3, %4 : i64, i32) -> i32
  phs.yield %5 : i32
}

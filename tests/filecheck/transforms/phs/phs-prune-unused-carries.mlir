// RUN: snax-opt %s -p phs-encode,phs-prune-unused-carries --split-input-file | filecheck %s

// Element-wise add: linalg `outs` block-arg %out is unused in the body. The
// encode pass keeps it as a carry, then the prune pass drops it because it
// has no uses in the merged PE body. Final PE has only the two pure inputs.

func.func @ker_parallel(%arg0: tensor<?xi32>, %arg1: tensor<?xi32>) -> tensor<?xi32> {
  %c0 = arith.constant 0 : index
  %dim = tensor.dim %arg0, %c0 : tensor<?xi32>
  %init = tensor.empty(%dim) : tensor<?xi32>
  %r = linalg.generic {
    indexing_maps = [affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>, affine_map<(d0) -> (d0)>],
    iterator_types = ["parallel"]
  } ins(%arg0, %arg1 : tensor<?xi32>, tensor<?xi32>)
    outs(%init : tensor<?xi32>) attrs = {"phs_acc" = @parallel_acc} {
  ^bb0(%a: i32, %b: i32, %out: i32):
    %s = arith.addi %a, %b : i32
    linalg.yield %s : i32
  } -> tensor<?xi32>
  return %r : tensor<?xi32>
}

// CHECK-LABEL: phs.pe @parallel_acc
// CHECK-SAME: with %0 (%a : i32, %b : i32) {

// -----

// Reduction-style accumulator: linalg `outs` block-arg %out IS used (carry of
// the sum). Encode keeps it; prune sees the use and keeps it too — final PE
// retains the carry input.

func.func @ker_reduction(%arg0: tensor<?x?xi32>, %arg1: tensor<?xi32>) -> tensor<?xi32> {
  %r = linalg.generic {
    indexing_maps = [affine_map<(d0, d1) -> (d0, d1)>, affine_map<(d0, d1) -> (d1)>],
    iterator_types = ["reduction", "parallel"]
  } ins(%arg0 : tensor<?x?xi32>) outs(%arg1 : tensor<?xi32>) attrs = {"phs_acc" = @reduction_acc} {
  ^bb0(%a: i32, %out: i32):
    %s = arith.addi %a, %out : i32
    linalg.yield %s : i32
  } -> tensor<?xi32>
  return %r : tensor<?xi32>
}

// CHECK-LABEL: phs.pe @reduction_acc
// CHECK-SAME: with %0 (%a : i32, %out : i32) {

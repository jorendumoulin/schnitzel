// RUN: snax-opt --split-input-file %s -p convert-snax-to-llvm --print-op-generic | filecheck %s

// Test: ClusterSyncOp lowers to inline asm (csrr x0, 0x810)

"builtin.module"() ({
  "func.func"() <{sym_name = "test_sync", function_type = () -> (), sym_visibility = "public"}> ({
    "snax.cluster_sync_op"() : () -> ()
    "func.return"() : () -> ()
  }) : () -> ()
}) : () -> ()

//CHECK:      "llvm.inline_asm"() <{asm_string = "csrr x0, 0x810"
//CHECK-SAME: has_side_effects
//CHECK-SAME: }> : () -> ()

// -----

// Test: HartIdOp lowers to inline asm (csrr $0, mhartid)

"builtin.module"() ({
  "func.func"() <{sym_name = "test_hart_id", function_type = () -> index, sym_visibility = "public"}> ({
    %0 = "snax.hart_id"() : () -> index
    "func.return"(%0) : (index) -> ()
  }) : () -> ()
}) : () -> ()

//CHECK:      %[[V0:.*]] = "llvm.inline_asm"() <{asm_string = "csrr $0, mhartid"
//CHECK-SAME: constraints = "=r"
//CHECK-SAME: }> : () -> i32
//CHECK-NEXT: %[[V1:.*]] = "builtin.unrealized_conversion_cast"(%[[V0]]) : (i32) -> index

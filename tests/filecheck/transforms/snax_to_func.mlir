// RUN: snax-opt --split-input-file %s -p snax-to-func --print-op-generic | filecheck %s

// ClusterSyncOp is no longer lowered by snax-to-func;
// it passes through and is handled by snax-to-llvm instead.

"builtin.module"() ({
  "snax.cluster_sync_op"() : () -> ()
}) : () -> ()

//CHECK: "builtin.module"() ({
//CHECK-NEXT:   "snax.cluster_sync_op"() : () -> ()
//CHECK-NEXT: }) : () -> ()

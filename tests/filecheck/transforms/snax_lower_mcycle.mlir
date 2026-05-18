// RUN: snax-opt %s -p snax-lower-mcycle --print-op-generic | filecheck %s

  "snax.mcycle"() : () -> ()
//func.func @mcycle () -> () {
//  "snax.mcycle"() : () -> ()
//  func.return
//  }

// CHECK: "llvm.inline_asm"() <{asm_string = "csrr zero, mcycle", constraints = "~{memory}", has_side_effects, tail_call_kind = #llvm.tailcallkind<none>}> : () -> ()

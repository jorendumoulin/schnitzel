// RUN: snax-opt %s -p instantiate-pe-array | filecheck %s

// When no template_spec is provided (CLI default), the pass is a no-op
// and preserves the IR unchanged.

phs.pe @myfirstaccelerator with %0 (%1 : i32, %2 : i32) {
  %3 = phs.choose @_0 with %0 (%1 : i32, %2 : i32) -> i32
    0) (%4, %5) {
      %6 = arith.muli %4, %5 : i32
      phs.yield %6 : i32
    }
    1) (%7, %8) {
      %9 = arith.addi %7, %8 : i32
      phs.yield %9 : i32
    }
  phs.yield %3 : i32
}

// CHECK: builtin.module {
// CHECK-NEXT:   phs.pe @myfirstaccelerator with %0 (%1 : i32, %2 : i32) {
// CHECK-NEXT:     %3 = phs.choose @_0 with %0 (%1 : i32, %2 : i32) -> i32
// CHECK-NEXT:       0) (%4, %5) {
// CHECK-NEXT:         %6 = arith.muli %4, %5 : i32
// CHECK-NEXT:         phs.yield %6 : i32
// CHECK-NEXT:       }
// CHECK-NEXT:       1) (%7, %8) {
// CHECK-NEXT:         %9 = arith.addi %7, %8 : i32
// CHECK-NEXT:         phs.yield %9 : i32
// CHECK-NEXT:       }
// CHECK-NEXT:     phs.yield %3 : i32
// CHECK-NEXT:   }
// CHECK-NEXT: }

// RUN: snax-opt %s -p phs-expand-integer-minmax | filecheck %s

func.func @clamp_i32(%a : i32, %lo : i32, %hi : i32) -> (i32, i32, i32, i32) {
  %0 = arith.maxsi %a, %lo : i32
  %1 = arith.minsi %0, %hi : i32
  %2 = arith.maxui %a, %lo : i32
  %3 = arith.minui %a, %hi : i32
  return %0, %1, %2, %3 : i32, i32, i32, i32
}

// CHECK-LABEL: @clamp_i32
// CHECK: %{{.*}} = arith.cmpi sgt, %a, %lo : i32
// CHECK: %{{.*}} = arith.select %{{.*}}, %a, %lo : i32
// CHECK: %{{.*}} = arith.cmpi slt
// CHECK: %{{.*}} = arith.select
// CHECK: %{{.*}} = arith.cmpi ugt
// CHECK: %{{.*}} = arith.select
// CHECK: %{{.*}} = arith.cmpi ult
// CHECK: %{{.*}} = arith.select
// CHECK-NOT: arith.maxsi
// CHECK-NOT: arith.minsi
// CHECK-NOT: arith.maxui
// CHECK-NOT: arith.minui

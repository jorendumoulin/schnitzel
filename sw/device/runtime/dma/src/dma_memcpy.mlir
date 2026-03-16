module {
  func.func public @memcpy_l3_l1(%arg0: memref<?xi8, "L3">, %arg1: memref<?xi8, "L1">) {
    "memref.copy"(%arg0, %arg1) : (memref<?xi8, "L3">, memref<?xi8, "L1">) -> ()
    return
  }
}

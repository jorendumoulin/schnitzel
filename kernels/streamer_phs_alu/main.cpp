#include <runtime.h>
#include <memref.hh>
#include <stdalign.h>
#include <stdint.h>

#define DATA_LEN 16

// MLIR-compiled kernel entry point
extern "C" void _mlir_ciface_streamer_add(MemRefDescriptor<int64_t, 1> *A,
                                          MemRefDescriptor<int64_t, 1> *B,
                                          MemRefDescriptor<int64_t, 1> *O);

// Test data in AXI/L3 memory (64-byte aligned for 512-bit AXI bus)
alignas(64) int64_t A[DATA_LEN] = {1, 2, 3, 4, 5, 6, 7, 8,
                                    9, 10, 11, 12, 13, 14, 15, 16};
alignas(64) int64_t B[DATA_LEN] = {10, 20, 30, 40, 50, 60, 70, 80,
                                    90, 100, 110, 120, 130, 140, 150, 160};
alignas(64) int64_t O[DATA_LEN] = {0};

// Expected: A + B
int64_t G[DATA_LEN] = {11, 22, 33, 44, 55, 66, 77, 88,
                        99, 110, 121, 132, 143, 154, 165, 176};

int main() {
  int hart = hart_id();

  MemRefDescriptor<int64_t, 1> memrefA = {A, A, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<int64_t, 1> memrefB = {B, B, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<int64_t, 1> memrefO = {O, O, 0, {DATA_LEN}, {1}};

  // The MLIR-compiled function handles DMA copies, accelerator CSR
  // programming, and synchronization internally.
  _mlir_ciface_streamer_add(&memrefA, &memrefB, &memrefO);

  cluster_sync();

  // Verify results (hart 1 only)
  int err = 0;
  if (hart == 1) {
    for (int i = 0; i < DATA_LEN; i++) {
      if (O[i] != G[i]) {
        verbose_printf("  ERROR: O[%d] = %d, expected %d\n", i, (int)O[i],
                       (int)G[i]);
        err++;
      }
    }

    if (err == 0) {
      printf("TEST PASSED!\n");
    } else {
      printf("TEST FAILED with %d errors.\n", err);
    }
  }

  // All harts wait here before exiting
  cluster_sync();
  htif_exit(err);
}

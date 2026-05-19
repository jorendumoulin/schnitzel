#include <memref.hh>
#include <runtime.h>
#include <stdalign.h>
#include <stdint.h>

#define DATA_LEN 16

// MLIR-compiled kernel entry point: two independent PHS accelerators.
// @acc1 (addi) writes D = A + B; @acc2 (xori) writes O = A ^ B.
extern "C" void _mlir_ciface_streamer_add(MemRefDescriptor<int32_t, 1> *A,
                                          MemRefDescriptor<int32_t, 1> *B,
                                          MemRefDescriptor<int32_t, 1> *D,
                                          MemRefDescriptor<int32_t, 1> *O);

// Test data in AXI/L3 memory (64-byte aligned for 512-bit AXI bus)
alignas(64) int32_t A[DATA_LEN] = {1, 2,  3,  4,  5,  6,  7,  8,
                                   9, 10, 11, 12, 13, 14, 15, 16};
alignas(64) int32_t B[DATA_LEN] = {10, 20,  30,  40,  50,  60,  70,  80,
                                   90, 100, 110, 120, 130, 140, 150, 160};
alignas(64) int32_t D[DATA_LEN] = {0};
alignas(64) int32_t O[DATA_LEN] = {0};

int32_t G_ADD[DATA_LEN];
int32_t G_XOR[DATA_LEN];

static void compute_golden() {
  for (int i = 0; i < DATA_LEN; i++) {
    G_ADD[i] = A[i] + B[i];
    G_XOR[i] = A[i] ^ B[i];
  }
}

int main() {
  int hart = hart_id();

  compute_golden();

  MemRefDescriptor<int32_t, 1> memrefA = {A, A, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<int32_t, 1> memrefB = {B, B, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<int32_t, 1> memrefD = {D, D, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<int32_t, 1> memrefO = {O, O, 0, {DATA_LEN}, {1}};

  // The MLIR-compiled function handles DMA copies, accelerator CSR
  // programming, and synchronization internally.
  unsigned long cycle_start = read_csr(0xb00); // mcycle
  _mlir_ciface_streamer_add(&memrefA, &memrefB, &memrefD, &memrefO);
  unsigned long cycle_end = read_csr(0xb00);

  cluster_sync();

  // Verify results (hart 1 only)
  int err = 0;
  if (hart == 1) {
    for (int i = 0; i < DATA_LEN; i++) {
      if (D[i] != G_ADD[i]) {
        printf("  ERROR: D[%d] = %d, expected %d\n", i, D[i], G_ADD[i]);
        err++;
      }
      if (O[i] != G_XOR[i]) {
        printf("  ERROR: O[%d] = %d, expected %d\n", i, O[i], G_XOR[i]);
        err++;
      }
    }

    printf("Kernel cycles: %d\n", (int)(cycle_end - cycle_start));

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

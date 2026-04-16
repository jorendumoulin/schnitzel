#include <memref.hh>
#include <runtime.h>
#include <stdalign.h>
#include <stdint.h>

#define T 4
#define I 4

extern "C" void _mlir_ciface_streamer_acc(MemRefDescriptor<int32_t, 2> *A,
                                          MemRefDescriptor<int32_t, 1> *C);

alignas(64) int32_t A[T][I] = {
    {1, 2, 3, 4},
    {10, 20, 30, 40},
    {100, 200, 300, 400},
    {1000, 2000, 3000, 4000},
};
alignas(64) int32_t C[I] = {0, 0, 0, 0};

// Expected: C_initial + sum_t A[t, i] = {1111, 2222, 3333, 4444}
int32_t G[I] = {1111, 2222, 3333, 4444};

int main() {
  int hart = hart_id();

  MemRefDescriptor<int32_t, 2> memrefA = {A[0], A[0], 0, {T, I}, {I, 1}};
  MemRefDescriptor<int32_t, 1> memrefC = {C, C, 0, {I}, {1}};

  unsigned long cycle_start = read_csr(0xb00);
  _mlir_ciface_streamer_acc(&memrefA, &memrefC);
  unsigned long cycle_end = read_csr(0xb00);

  cluster_sync();

  int err = 0;
  if (hart == 1) {
    for (int i = 0; i < I; i++) {
      if (C[i] != G[i]) {
        verbose_printf("  ERROR: C[%d] = %d, expected %d\n", i, C[i], G[i]);
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

  cluster_sync();
  htif_exit(err);
}

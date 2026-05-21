#include <memref.hh>
#include <runtime.h>
#include <stdalign.h>
#include <stdint.h>

#define DIM0 16
#define DIM1 4
#define DATA_LEN (DIM0 * DIM1)

extern "C" void _mlir_ciface_streamer_add(MemRefDescriptor<int32_t, 2> *A,
                                          MemRefDescriptor<int32_t, 2> *B,
                                          MemRefDescriptor<int32_t, 2> *N);

alignas(64) int32_t A[DATA_LEN];
alignas(64) int32_t B[DATA_LEN];
alignas(64) int32_t N[DATA_LEN];

int main() {
  MemRefDescriptor<int32_t, 2> memrefA = {A, A, 0, {DIM0, DIM1}, {DIM1, 1}};
  MemRefDescriptor<int32_t, 2> memrefB = {B, B, 0, {DIM0, DIM1}, {DIM1, 1}};
  MemRefDescriptor<int32_t, 2> memrefN = {N, N, 0, {DIM0, DIM1}, {DIM1, 1}};

  unsigned long cycle_start = read_csr(0xb00);
  _mlir_ciface_streamer_add(&memrefA, &memrefB, &memrefN);
  unsigned long cycle_end = read_csr(0xb00);

  cluster_sync();
  if (hart_id() == 1) {
    printf("Kernel cycles: %d\n", (int)(cycle_end - cycle_start));
  }
  cluster_sync();
  htif_exit(0);
}

#include <memref.hh>
#include <runtime.h>
#include <stdalign.h>
#include <stdint.h>

#define DATA_LEN 16

extern "C" void _mlir_ciface_streamer_add(MemRefDescriptor<int32_t, 1> *A,
                                          MemRefDescriptor<int32_t, 1> *B,
                                          MemRefDescriptor<int32_t, 1> *D,
                                          MemRefDescriptor<int32_t, 1> *O);

alignas(64) int32_t A[DATA_LEN];
alignas(64) int32_t B[DATA_LEN];
alignas(64) int32_t D[DATA_LEN];
alignas(64) int32_t O[DATA_LEN];

int main() {
  MemRefDescriptor<int32_t, 1> memrefA = {A, A, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<int32_t, 1> memrefB = {B, B, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<int32_t, 1> memrefD = {D, D, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<int32_t, 1> memrefO = {O, O, 0, {DATA_LEN}, {1}};

  unsigned long cycle_start = read_csr(0xb00);
  _mlir_ciface_streamer_add(&memrefA, &memrefB, &memrefD, &memrefO);
  unsigned long cycle_end = read_csr(0xb00);

  cluster_sync();
  if (hart_id() == 1) {
    printf("Kernel cycles: %d\n", (int)(cycle_end - cycle_start));
  }
  cluster_sync();
  htif_exit(0);
}

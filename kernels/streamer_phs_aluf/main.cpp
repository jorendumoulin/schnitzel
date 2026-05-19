#include <memref.hh>
#include <runtime.h>
#include <stdalign.h>
#include <stdint.h>

#define DATA_LEN 16

extern "C" void _mlir_ciface_streamer_add(MemRefDescriptor<float, 1> *A,
                                          MemRefDescriptor<float, 1> *B,
                                          MemRefDescriptor<float, 1> *O);

alignas(64) uint32_t A[DATA_LEN];
alignas(64) uint32_t B[DATA_LEN];
alignas(64) uint32_t O[DATA_LEN];

int main() {
  float *Af = reinterpret_cast<float *>(A);
  float *Bf = reinterpret_cast<float *>(B);
  float *Of = reinterpret_cast<float *>(O);

  MemRefDescriptor<float, 1> memrefA = {Af, Af, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<float, 1> memrefB = {Bf, Bf, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<float, 1> memrefO = {Of, Of, 0, {DATA_LEN}, {1}};

  unsigned long cycle_start = read_csr(0xb00);
  _mlir_ciface_streamer_add(&memrefA, &memrefB, &memrefO);
  unsigned long cycle_end = read_csr(0xb00);

  cluster_sync();
  if (hart_id() == 1) {
    printf("Kernel cycles: %d\n", (int)(cycle_end - cycle_start));
  }
  cluster_sync();
  htif_exit(0);
}

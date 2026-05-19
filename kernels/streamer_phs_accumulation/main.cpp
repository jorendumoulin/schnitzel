#include <memref.hh>
#include <runtime.h>
#include <stdalign.h>
#include <stdint.h>

#define T 4
#define I 4

extern "C" void _mlir_ciface_streamer_acc(MemRefDescriptor<int32_t, 2> *A,
                                          MemRefDescriptor<int32_t, 1> *C);

alignas(64) int32_t A[T][I];
alignas(64) int32_t C[I];

int main() {
  MemRefDescriptor<int32_t, 2> memrefA = {A[0], A[0], 0, {T, I}, {I, 1}};
  MemRefDescriptor<int32_t, 1> memrefC = {C, C, 0, {I}, {1}};

  unsigned long cycle_start = read_csr(0xb00);
  _mlir_ciface_streamer_acc(&memrefA, &memrefC);
  unsigned long cycle_end = read_csr(0xb00);

  cluster_sync();
  if (hart_id() == 1) {
    printf("Kernel cycles: %d\n", (int)(cycle_end - cycle_start));
  }
  cluster_sync();
  htif_exit(0);
}

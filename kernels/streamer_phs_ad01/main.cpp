#include <memref.hh>
#include <runtime.h>
#include <stdalign.h>
#include <stdint.h>

#define T 4
#define I 4

// Two-stage f32 kernel, all stages handled by the same PHS accelerator:
//   1. FC-style reduction:  C[i] += sum_t A[t, i] * W[t, i]
//   2. Clamp activation:    C[i]  = max(min(C[i], HI[i]), LO[i])
//
// Ibex has no FPU, so we keep all data as uint32_t bit patterns and only
// reinterpret to float* at the memref-descriptor boundary.
extern "C" void _mlir_ciface_streamer_ad01(MemRefDescriptor<float, 2> *A,
                                           MemRefDescriptor<float, 2> *W,
                                           MemRefDescriptor<float, 1> *C,
                                           MemRefDescriptor<float, 1> *HI,
                                           MemRefDescriptor<float, 1> *LO);

// A[t, i] = t * 4 + i + 1   (i.e. 1..16 row-major)
alignas(64) uint32_t A[T][I] = {
    {0x3f800000, 0x40000000, 0x40400000, 0x40800000}, //  1,  2,  3,  4
    {0x40a00000, 0x40c00000, 0x40e00000, 0x41000000}, //  5,  6,  7,  8
    {0x41100000, 0x41200000, 0x41300000, 0x41400000}, //  9, 10, 11, 12
    {0x41500000, 0x41600000, 0x41700000, 0x41800000}, // 13, 14, 15, 16
};

// W[t, i] = 1.0 for all entries — reduces the FC to column-sum of A.
alignas(64) uint32_t W[T][I] = {
    {0x3f800000, 0x3f800000, 0x3f800000, 0x3f800000},
    {0x3f800000, 0x3f800000, 0x3f800000, 0x3f800000},
    {0x3f800000, 0x3f800000, 0x3f800000, 0x3f800000},
    {0x3f800000, 0x3f800000, 0x3f800000, 0x3f800000},
};

alignas(64) uint32_t C[I] = {0, 0, 0, 0};

// Clamp thresholds (broadcast across all output channels).
alignas(64) uint32_t HI[I] = {0x41f00000, 0x41f00000, 0x41f00000, 0x41f00000}; // 30.0
alignas(64) uint32_t LO[I] = {0, 0, 0, 0};                                     //  0.0

// Expected column sums clamped to [0.0, 30.0]:
//   col 0:  1 +  5 +  9 + 13 = 28  -> 28 = 0x41e00000
//   col 1:  2 +  6 + 10 + 14 = 32  -> 30 = 0x41f00000
//   col 2:  3 +  7 + 11 + 15 = 36  -> 30 = 0x41f00000
//   col 3:  4 +  8 + 12 + 16 = 40  -> 30 = 0x41f00000
uint32_t G[I] = {0x41e00000, 0x41f00000, 0x41f00000, 0x41f00000};

int main() {
  int hart = hart_id();

  float *Af = reinterpret_cast<float *>(A[0]);
  float *Wf = reinterpret_cast<float *>(W[0]);
  float *Cf = reinterpret_cast<float *>(C);
  float *HIf = reinterpret_cast<float *>(HI);
  float *LOf = reinterpret_cast<float *>(LO);

  MemRefDescriptor<float, 2> memrefA = {Af, Af, 0, {T, I}, {I, 1}};
  MemRefDescriptor<float, 2> memrefW = {Wf, Wf, 0, {T, I}, {I, 1}};
  MemRefDescriptor<float, 1> memrefC = {Cf, Cf, 0, {I}, {1}};
  MemRefDescriptor<float, 1> memrefHI = {HIf, HIf, 0, {I}, {1}};
  MemRefDescriptor<float, 1> memrefLO = {LOf, LOf, 0, {I}, {1}};

  unsigned long cycle_start = read_csr(0xb00);
  _mlir_ciface_streamer_ad01(&memrefA, &memrefW, &memrefC, &memrefHI,
                             &memrefLO);
  unsigned long cycle_end = read_csr(0xb00);

  cluster_sync();

  int err = 0;
  if (hart == 1) {
    for (int i = 0; i < I; i++) {
      if (C[i] != G[i]) {
        verbose_printf("  ERROR: C[%d] = 0x%08x, expected 0x%08x\n", i, C[i],
                       G[i]);
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

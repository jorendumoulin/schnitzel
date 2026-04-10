#include <memref.hh>
#include <runtime.h>
#include <stdalign.h>
#include <stdint.h>

#define DATA_LEN 16

// MLIR-compiled kernel entry point (f32 memrefs, but Ibex has no FPU so we
// pass bit-exact uint32_t data through reinterpret_cast).
extern "C" void _mlir_ciface_streamer_add(MemRefDescriptor<float, 1> *A,
                                          MemRefDescriptor<float, 1> *B,
                                          MemRefDescriptor<float, 1> *O);

// IEEE 754 f32 test data stored as uint32_t to avoid FPU usage.
// A = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
//       9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0}
alignas(64) uint32_t A[DATA_LEN] = {
    0x3f800000, 0x40000000, 0x40400000, 0x40800000, //  1,  2,  3,  4
    0x40a00000, 0x40c00000, 0x40e00000, 0x41000000, //  5,  6,  7,  8
    0x41100000, 0x41200000, 0x41300000, 0x41400000, //  9, 10, 11, 12
    0x41500000, 0x41600000, 0x41700000, 0x41800000, // 13, 14, 15, 16
};

// B = {10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0,
//       90.0, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0}
alignas(64) uint32_t B[DATA_LEN] = {
    0x41200000, 0x41a00000, 0x41f00000, 0x42200000, //  10,  20,  30,  40
    0x42480000, 0x42700000, 0x428c0000, 0x42a00000, //  50,  60,  70,  80
    0x42b40000, 0x42c80000, 0x42dc0000, 0x42f00000, //  90, 100, 110, 120
    0x43020000, 0x430c0000, 0x43160000, 0x43200000, // 130, 140, 150, 160
};

alignas(64) uint32_t O[DATA_LEN] = {0};

// Expected: A + B (bit-exact IEEE 754 f32)
// {11.0, 22.0, 33.0, 44.0, 55.0, 66.0, 77.0, 88.0,
//   99.0, 110.0, 121.0, 132.0, 143.0, 154.0, 165.0, 176.0}
uint32_t G[DATA_LEN] = {
    0x41300000, 0x41b00000, 0x42040000, 0x42300000, //  11,  22,  33,  44
    0x425c0000, 0x42840000, 0x429a0000, 0x42b00000, //  55,  66,  77,  88
    0x42c60000, 0x42dc0000, 0x42f20000, 0x43040000, //  99, 110, 121, 132
    0x430f0000, 0x431a0000, 0x43250000, 0x43300000, // 143, 154, 165, 176
};

int main() {
  int hart = hart_id();

  // Cast uint32_t* data to float* for the f32 memref descriptors.
  // The Ibex has no FPU — the accelerator handles float arithmetic.
  float *Af = reinterpret_cast<float *>(A);
  float *Bf = reinterpret_cast<float *>(B);
  float *Of = reinterpret_cast<float *>(O);

  MemRefDescriptor<float, 1> memrefA = {Af, Af, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<float, 1> memrefB = {Bf, Bf, 0, {DATA_LEN}, {1}};
  MemRefDescriptor<float, 1> memrefO = {Of, Of, 0, {DATA_LEN}, {1}};

  unsigned long cycle_start = read_csr(0xb00); // mcycle
  _mlir_ciface_streamer_add(&memrefA, &memrefB, &memrefO);
  unsigned long cycle_end = read_csr(0xb00);

  cluster_sync();

  // Bit-exact comparison (no FPU needed)
  int err = 0;
  if (hart == 1) {
    for (int i = 0; i < DATA_LEN; i++) {
      if (O[i] != G[i]) {
        verbose_printf("  ERROR: O[%d] = 0x%08x, expected 0x%08x\n", i, O[i],
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

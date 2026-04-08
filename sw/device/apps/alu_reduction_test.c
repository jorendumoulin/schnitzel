#include <runtime.h>
#include <stdalign.h>

#define TEST_SIZE 16
#define REDUCE_SIZE 4

// Test input data in AXI/L3 memory (64-byte aligned for 512-bit AXI bus)
alignas(64) int a_test_data[TEST_SIZE] = {0, 1, 2,  3,  4,  5,  6,  7,
                                          8, 9, 10, 11, 12, 13, 14, 15};

// TCDM buffers
TCDM int tcdm_a_data[TEST_SIZE];
TCDM int tcdm_c_data[TEST_SIZE];

// Expected results for reduction: C[i] = sum_j A[i + 4*j] for j=0..3
// C[0] = 0+4+8+12 = 24, C[1] = 1+5+9+13 = 28, C[2] = 2+6+10+14 = 32, C[3] =
// 3+7+11+15 = 36
int c_reduction_expected[REDUCE_SIZE] = {24, 28, 32, 36};

// Expected results for in-place readWrite: C[i] = C_initial[i] + A[i]
// C_initial[i] = 100 + i, A[i] = i => C[i] = 100 + 2*i
int c_inplace_expected[TEST_SIZE] = {100, 102, 104, 106, 108, 110, 112, 114,
                                     116, 118, 120, 122, 124, 126, 128, 130};

inline int check_results(int *test_data, int *reference_data, int count) {
  unsigned int fail_count = 0;
  for (int i = 0; i < count; i++) {
    if (test_data[i] != reference_data[i]) {
      verbose_printf("  ERROR: Mismatch at index %d! Expected %d, Got %d\n", i,
                     reference_data[i], test_data[i]);
      fail_count++;
    } else {
      verbose_printf("  [%d] OK: %d\n", i, test_data[i]);
    }
  }
  return fail_count;
}

// Program DMA (hart 2 / core_0) to transfer TEST_SIZE words between AXI and
// TCDM dir=0: AXI->TCDM, dir=1: TCDM->AXI
void dma_transfer(int *tcdm_addr, int *axi_addr, int dir) {
  write_csr(0x900, (unsigned long)tcdm_addr);
  write_csr(0x901, 0x0);
  write_csr(0x902, 0x0);
  write_csr(0x903, 0x0);
  write_csr(0x904, 0x200);
  write_csr(0x905, 0x0);
  write_csr(0x906, 0x0);
  write_csr(0x907, 0x0);
  write_csr(0x908, 0x1);
  write_csr(0x909, 0x20);
  write_csr(0x90a, 0x10);
  write_csr(0x90b, 0x8);
  write_csr(0x90c, 0x4);
  write_csr(0x90d, (unsigned long)axi_addr);
  write_csr(0x90e, 0x0);
  write_csr(0x90f, 0x0);
  write_csr(0x910, 0x0);
  write_csr(0x911, 0x200);
  write_csr(0x912, 0x0);
  write_csr(0x913, 0x0);
  write_csr(0x914, 0x0);
  write_csr(0x915, 0x1);
  write_csr(0x916, dir);
  write_csr(0x917, 0x1);
  read_csr(0x917);
}

int main() {
  int hart = hart_id();
  static int fail_count = 0;

  // --- PHASE 1: Copy A data from AXI to TCDM using DMA ---
  if (hart == 1) {
    verbose_printf("=== ALU Reduction Test ===\n");
  }
  cluster_sync();

  if (hart == 2) {
    verbose_printf("DMA: Copying A data to TCDM...\n");
    dma_transfer(tcdm_a_data, a_test_data, 0);
    verbose_printf("DMA: Done.\n");
  }
  cluster_sync();

  // --- PHASE 2: Reduction test: C[i] = sum_j A[i + 4*j] ---
  if (hart == 1) {
    verbose_printf("--- Reduction Test ---\n");
    // Initialize C to zero in TCDM
    for (int i = 0; i < REDUCE_SIZE; i++)
      tcdm_c_data[i] = 0;

    // A streamer: 1 temporal dim, spatial unroll 4
    write_csr(0x900, (unsigned long)tcdm_a_data); // A base
    write_csr(0x901, 16); // A temporal stride: 4 elements * 4 bytes
    write_csr(0x902, 4);  // A temporal bound: 4 iterations
    write_csr(0x903, 4);  // A spatial stride: 4 bytes

    // B streamer: unused in readWrite mode (won't be started)
    write_csr(0x904, 0);
    write_csr(0x905, 0);
    write_csr(0x906, 0);
    write_csr(0x907, 0);

    // C streamer: 2 temporal dims, reduction on dim 0
    write_csr(0x908, (unsigned long)tcdm_c_data); // C base
    write_csr(0x909, 0); // C temporal stride 1 (outer, unused, bound=0)
    write_csr(0x90A, 0); // C temporal stride 0 (inner, reduction: stride=0)
    write_csr(0x90B, 0); // C temporal bound 1 (outer, unused)
    write_csr(0x90C, 4); // C temporal bound 0 (inner, 4 reduction iterations)
    write_csr(0x90D, 4); // C spatial stride: 4 bytes

    write_csr(0x90E, 0); // ALU select: addition
    write_csr(0x90F, 1); // Mode: readWrite (reduction)

    write_csr(0x910, 0x1); // Start
    read_csr(0x910);       // Wait for completion
    verbose_printf("ALU reduction done.\n");
  }
  cluster_sync();

  // Verify reduction results
  if (hart == 1) {
    verbose_printf("Verifying reduction results:\n");
    fail_count += check_results(tcdm_c_data, c_reduction_expected, REDUCE_SIZE);
  }
  cluster_sync();

  // --- PHASE 3: Non-reduction readWrite: C[i] = C_initial[i] + A[i] ---
  if (hart == 1) {
    verbose_printf("--- Non-Reduction ReadWrite Test ---\n");
    // Initialize C with known values
    for (int i = 0; i < TEST_SIZE; i++)
      tcdm_c_data[i] = 100 + i;

    // A streamer: same as before
    write_csr(0x900, (unsigned long)tcdm_a_data); // A base
    write_csr(0x901, 16);                         // A temporal stride
    write_csr(0x902, 4); // A temporal bound: 4 iterations
    write_csr(0x903, 4); // A spatial stride

    // B streamer: unused
    write_csr(0x904, 0);
    write_csr(0x905, 0);
    write_csr(0x906, 0);
    write_csr(0x907, 0);

    // C streamer: 2 temporal dims, NO reduction (all strides non-zero)
    write_csr(0x908, (unsigned long)tcdm_c_data); // C base
    write_csr(0x909, 0); // C temporal stride 1 (outer, unused, bound=0)
    write_csr(0x90A,
              16); // C temporal stride 0 (inner, stride=16: iterate normally)
    write_csr(0x90B, 0); // C temporal bound 1 (outer, unused)
    write_csr(0x90C, 4); // C temporal bound 0 (inner, 4 iterations)
    write_csr(0x90D, 4); // C spatial stride: 4 bytes

    write_csr(0x90E, 0); // ALU select: addition
    write_csr(0x90F, 1); // Mode: readWrite (but no reduction since stride != 0)

    write_csr(0x910, 0x1); // Start
    read_csr(0x910);       // Wait for completion
    verbose_printf("ALU in-place readWrite done.\n");
  }
  cluster_sync();

  // Verify in-place results
  if (hart == 1) {
    verbose_printf("Verifying in-place readWrite results:\n");
    fail_count += check_results(tcdm_c_data, c_inplace_expected, TEST_SIZE);
    if (fail_count == 0) {
      printf("TEST PASSED!\n");
    } else {
      printf("TEST FAILED with %d errors.\n", fail_count);
    }
    htif_exit(fail_count);
  }
  cluster_sync();
  htif_exit(0);
}

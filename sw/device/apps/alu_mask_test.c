#include <runtime.h>
#include <stdalign.h>

#define TEST_SIZE 16
#define SENTINEL 0xDEADBEEF

alignas(64) int a_test_data[TEST_SIZE] = {0, 1, 2,  3,  4,  5,  6,  7,
                                          8, 9, 10, 11, 12, 13, 14, 15};

alignas(64) int b_test_data[TEST_SIZE] = {0,    2,    4,     8,    16,   32,
                                          64,   128,  256,   512,  1024, 2048,
                                          4096, 8192, 16384, 32768};

// With dim 0 masked off, only lane 0 of each 4-element temporal iteration
// is active, so only indices {0, 4, 8, 12} get written. The rest keep SENTINEL.
int c_expected[TEST_SIZE];

TCDM int tcdm_a_data[TEST_SIZE];
TCDM int tcdm_b_data[TEST_SIZE];
TCDM int tcdm_c_data[TEST_SIZE];

inline int check_results(int *test_data, int *reference_data,
                         size_t test_size) {
  unsigned int fail_count = 0;
  for (int i = 0; i < TEST_SIZE; i++) {
    if (test_data[i] != reference_data[i]) {
      verbose_printf(
          "  ERROR: Mismatch at index %d! Expected 0x%08x, Got 0x%08x\n", i,
          reference_data[i], test_data[i]);
      fail_count++;
    } else {
      verbose_printf("  [%d] OK: 0x%08x\n", i, test_data[i]);
    }
  }
  return fail_count;
}

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

  if (hart == 1) {
    verbose_printf("=== ALU Mask Test (dim 0 disabled) ===\n");
    for (int i = 0; i < TEST_SIZE; i++) {
      c_expected[i] =
          (i % 4 == 0) ? (a_test_data[i] + b_test_data[i]) : (int)SENTINEL;
      tcdm_c_data[i] = (int)SENTINEL;
    }
  }
  cluster_sync();

  if (hart == 2) {
    dma_transfer(tcdm_a_data, a_test_data, 0);
    dma_transfer(tcdm_b_data, b_test_data, 0);
  }
  cluster_sync();

  if (hart == 1) {
    // A streamer
    write_csr(0x900, (unsigned long)tcdm_a_data);
    write_csr(0x901, 16);
    write_csr(0x902, 4);
    write_csr(0x903, 4);

    // B streamer
    write_csr(0x904, (unsigned long)tcdm_b_data);
    write_csr(0x905, 16);
    write_csr(0x906, 4);
    write_csr(0x907, 4);

    // C streamer
    write_csr(0x908, (unsigned long)tcdm_c_data);
    write_csr(0x909, 16);
    write_csr(0x90A, 0);
    write_csr(0x90B, 4);
    write_csr(0x90C, 0);
    write_csr(0x90D, 4);

    write_csr(0x90E, 0);   // ALU select: addition
    write_csr(0x90F, 0);   // Mode: normal
    write_csr(0x910, 0x0); // Spatial dim mask: bit 0 cleared — dim 0 collapsed

    write_csr(0x911, 0x1);
    read_csr(0x911);
    verbose_printf("ALU: Done.\n");
  }
  cluster_sync();

  if (hart == 1) {
    verbose_printf("Verifying masked ALU results:\n");
    fail_count += check_results(tcdm_c_data, c_expected, TEST_SIZE);
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

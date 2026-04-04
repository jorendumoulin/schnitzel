#include <runtime.h>
#include <stdalign.h>

#define TEST_SIZE 16

// Test input data in AXI/L3 memory (64-byte aligned for 512-bit AXI bus)
alignas(64) int a_test_data[TEST_SIZE] = {0, 1, 2,  3,  4,  5,  6,  7,
                                          8, 9, 10, 11, 12, 13, 14, 15};

alignas(64) int b_test_data[TEST_SIZE] = {0,    2,    4,     8,    16,   32,
                                          64,   128,  256,   512,  1024, 2048,
                                          4096, 8192, 16384, 32768};

// Expected results for addition: a + b
int c_expected[TEST_SIZE] = {0,   3,   6,    11,   20,   37,   70,    135,
                             264, 521, 1034, 2059, 4108, 8205, 16398, 32783};

// TCDM buffers
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
      verbose_printf("  [%d] OK: %d\n", i, test_data[i]);
    }
  }
  return fail_count;
}

// Program DMA (hart 2 / core_0) to transfer TEST_SIZE words between AXI and
// TCDM dir=0: AXI->TCDM, dir=1: TCDM->AXI
void dma_transfer(int *tcdm_addr, int *axi_addr, int dir) {
  // TCDM streamer config: 4 temporal dims, spatial unroll (2,2,2,2)=16 ports
  write_csr(0x900, (unsigned long)tcdm_addr); // TCDM base address
  // Temporal strides (dims 3,2,1,0 at CSRs 0x901-0x904):
  write_csr(0x901, 0x0);
  write_csr(0x902, 0x0);
  write_csr(0x903, 0x0);
  write_csr(0x904, 0x200); // stride for dim 0 (unused when bound=1)
  // Temporal bounds:
  write_csr(0x905, 0x0);
  write_csr(0x906, 0x0);
  write_csr(0x907, 0x0);
  write_csr(0x908, 0x1); // bound=1: single iteration transfers all 16 elements
  // Spatial strides (2,2,2,2 unrolling covers 16 contiguous words):
  write_csr(0x909, 0x20); // dim 3: stride 32
  write_csr(0x90a, 0x10); // dim 2: stride 16
  write_csr(0x90b, 0x8);  // dim 1: stride 8
  write_csr(0x90c, 0x4);  // dim 0: stride 4

  // AXI streamer config: 4 temporal dims, no spatial unroll (512-bit wide)
  write_csr(0x90d, (unsigned long)axi_addr); // AXI base address
  write_csr(0x90e, 0x0);
  write_csr(0x90f, 0x0);
  write_csr(0x910, 0x0);
  write_csr(0x911, 0x200);
  write_csr(0x912, 0x0);
  write_csr(0x913, 0x0);
  write_csr(0x914, 0x0);
  write_csr(0x915, 0x1);

  write_csr(0x916, dir); // Direction: 0=AXI->TCDM, 1=TCDM->AXI
  write_csr(0x917, 0x1); // Start
  read_csr(0x917);       // Wait for completion
}

int main() {
  int hart = hart_id();
  static int fail_count = 0;

  // --- PHASE 1: Copy A and B test data from AXI to TCDM using DMA ---
  if (hart == 1) {
    verbose_printf("=== ALU Accelerator Test ===\n");
    verbose_printf("TCDM A: %p, TCDM B: %p, TCDM C: %p\n", tcdm_a_data,
                   tcdm_b_data, tcdm_c_data);
  }
  cluster_sync();

  if (hart == 2) {
    verbose_printf("DMA: Copying A data to TCDM...\n");
    dma_transfer(tcdm_a_data, a_test_data, 0);
    verbose_printf("DMA: Copying B data to TCDM...\n");
    dma_transfer(tcdm_b_data, b_test_data, 0);
    verbose_printf("DMA: Done.\n");
  }
  cluster_sync();

  // --- PHASE 2: Verify DMA copied data correctly ---
  if (hart == 1) {
    verbose_printf("Verifying A data in TCDM:\n");
    fail_count += check_results(tcdm_a_data, a_test_data, TEST_SIZE);
    verbose_printf("Verifying B data in TCDM:\n");
    fail_count += check_results(tcdm_b_data, b_test_data, TEST_SIZE);
    if (fail_count > 0) {
      printf("DMA COPY FAILED with %d errors.\n", fail_count);
      htif_exit(fail_count);
    }
    verbose_printf("DMA data verified OK.\n");
  }
  cluster_sync();

  // --- PHASE 3: Program ALU accelerator to compute C = A + B ---
  if (hart == 1) {
    verbose_printf("ALU: Programming accelerator (C = A + B)...\n");

    // A streamer: AffineAguConfig(1 temporal dim, spatial unroll 4)
    write_csr(0x900, (unsigned long)tcdm_a_data); // A base address
    write_csr(0x901, 16); // A temporal stride: 4 elements * 4 bytes
    write_csr(0x902, 4);  // A temporal bound: 4 iterations
    write_csr(0x903, 4);  // A spatial stride: 4 bytes (consecutive ints)

    // B streamer:
    write_csr(0x904, (unsigned long)tcdm_b_data); // B base address
    write_csr(0x905, 16);                         // B temporal stride
    write_csr(0x906, 4);                          // B temporal bound
    write_csr(0x907, 4);                          // B spatial stride

    // C streamer (2 temporal dims):
    write_csr(0x908, (unsigned long)tcdm_c_data); // C base address
    write_csr(0x909, 16);                         // C temporal stride 1 (outer)
    write_csr(0x90A, 0);                          // C temporal stride 0 (inner, unused)
    write_csr(0x90B, 4);                          // C temporal bound 1 (outer)
    write_csr(0x90C, 0);                          // C temporal bound 0 (inner, unused)
    write_csr(0x90D, 4);                          // C spatial stride

    // ALU operation: 0 = addition
    write_csr(0x90E, 0);
    // Mode: 0 = normal (C = A + B)
    write_csr(0x90F, 0);

    // Start and wait
    write_csr(0x910, 0x1);
    read_csr(0x910);
    verbose_printf("ALU: Done.\n");
  }
  cluster_sync();

  // --- PHASE 4: Verify ALU results ---
  if (hart == 1) {
    verbose_printf("Verifying ALU results (C = A + B):\n");
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

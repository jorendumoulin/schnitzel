#include <dma.h>
#include <runtime.h>
#include <stdalign.h>

// Assuming your TCDM and AXI base addresses
#define TEST_SIZE 16

// Global test data (Linker puts this in AXI/L3)
// Needs to be 512-bit aligned (64-bytes) to be picked up correctly over AXI
alignas(64) int axi_src_data[TEST_SIZE] = {
    0xDEAD, 0xBEEF, 0xCAFE, 0xBABE, 0x1234, 0x5678, 0xAAAA, 0x5555,
    0xDEAD, 0xBEEF, 0xCAFE, 0xBABE, 0x1234, 0x5678, 0xAAAA, 0x5555};

alignas(64) int axi_dest_data[TEST_SIZE];
TCDM int tcdm_dest_data[TEST_SIZE];

inline int check_results(int *test_data, int *reference_data,
                         size_t test_size) {
  unsigned int fail_count = 0;
  for (int i = 0; i < TEST_SIZE; i++) {
    if (test_data[i] != reference_data[i]) {
      verbose_printf(
          "  ERROR: Mismatch at index %d! Expected 0x%08x, Got 0x % 08x\n ", i,
          reference_data[i], test_data[i]);
      fail_count++;
    } else {
      verbose_printf("  [%d] OK: 0x%08x \n", i, test_data[i]);
    }
  }
  return fail_count;
}

int main() {
  verbose_printf("TCDM address %p : \n", &tcdm_dest_data);
  int hart = hart_id();
  static int fail_count = 0; // Static so it persists across syncs
  if (hart == 1) {
    verbose_printf("Starting DMA Loopback Test: AXI -> TCDM -> AXI_NEW\n");
    verbose_printf("Initial AXI Source Values:\n");
    for (int i = 0; i < TEST_SIZE; i++) {
      verbose_printf("  [%d] %p : 0x%08x\n", i, &axi_src_data[i],
                     axi_src_data[i]);
    }
  }
  cluster_sync();

  // --- PHASE 1: AXI -> TCDM ---
  // Call dma_memcpy
  dma_memcpy(tcdm_dest_data, axi_src_data, sizeof(axi_src_data));
  if (hart == 2) {
    verbose_printf("DMA done\n");
  }
  cluster_sync();
  if (hart == 1) {
    fail_count += check_results(tcdm_dest_data, axi_src_data, TEST_SIZE);
  }
  cluster_sync();
  if (hart == 2) {
    // All settings remain the same, except for direction and destination
    // address in TCDM
    write_csr(0x90d, (unsigned long)axi_dest_data); // Dest: New AXI Location
    write_csr(0x916, 0x1);                          // Direction: TCDM -> AXI
    write_csr(0x917, 0x1);                          // Start
    read_csr(0x917);
    verbose_printf("DMA Double-Transfer Complete.\n");
  }
  cluster_sync();
  if (hart == 1) {
    verbose_printf("Validating Final Results at %p...\n", axi_dest_data);
    fail_count += check_results(axi_dest_data, axi_src_data, TEST_SIZE);
    if (fail_count == 0) {
      printf("TEST PASSED!\n");
    } else {
      printf("TEST FAILED with %d errors.\n", fail_count);
    }
    htif_exit(fail_count);
  }
  // Wait for hart 2 to finish with the core count
  cluster_sync();
  htif_exit(0);
}

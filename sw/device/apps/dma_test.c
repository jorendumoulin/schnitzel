#include <runtime.h>
#include <stdalign.h>

#define VERBOSE
#ifdef VERBOSE
// Correct: Expands to the real LOG_VERBOSE function
#define LOG_VERBOSE(...) printf(__VA_ARGS__)
#else
// Correct: Expands to nothing (a "no-op")
#define LOG_VERBOSE(...) ((void)0)
#endif
// Assuming your TCDM and AXI base addresses
#define TCDM_ADDR 0x10000000
#define TEST_SIZE 16

// Global test data (Linker puts this in AXI/L3)
alignas(64) int axi_src_data[TEST_SIZE] = {
    0xDEAD, 0xBEEF, 0xCAFE, 0xBABE, 0x1234, 0x5678, 0xAAAA, 0x5555,
    0xDEAD, 0xBEEF, 0xCAFE, 0xBABE, 0x1234, 0x5678, 0xAAAA, 0x5555};

alignas(64) int axi_dest_data[TEST_SIZE];
//__attribute__((section(".tcdm"))) int tcdm_dest_data[TEST_SIZE];

int main() {
  // LOG_VERBOSE("TCDM address %p : \n", &tcdm_dest_data);
  LOG_VERBOSE("TCDM address %p : \n", TCDM_ADDR);
  int hart = hart_id();
  static int fail_count = 0; // Static so it persists across syncs

  // --- PHASE 1: Initialization ---
  if (hart == 1) {
    LOG_VERBOSE("Starting DMA Loopback Test: AXI -> TCDM -> AXI_NEW\n");
  }
  cluster_sync();

  // --- PHASE 2: Core 2 Prints Initial State ---
  if (hart == 1) {
    LOG_VERBOSE("Initial AXI Source Values:\n");
    for (int i = 0; i < TEST_SIZE; i++) {
      LOG_VERBOSE("  [%d] %p : 0x%08x\n", i, &axi_src_data[i], axi_src_data[i]);
    }
  }
  cluster_sync();

  // --- PHASE 3: AXI -> TCDM ---
  if (hart == 2) {

    // Configure Streamer (TCDM Side):
    write_csr(0x900, TCDM_ADDR);
    // 4 Temporal strides:
    write_csr(0x901, 0x0);
    write_csr(0x902, 0x0);
    write_csr(0x903, 0x0);
    write_csr(0x904, 0x200);
    // 4 Temporal bounds:
    write_csr(0x905, 0x0);
    write_csr(0x906, 0x0);
    write_csr(0x907, 0x0);
    write_csr(0x908, 0x1);
    // 4 Spatial strides:
    write_csr(0x909, 0x20);
    write_csr(0x90a, 0x10);
    write_csr(0x90b, 0x8);
    write_csr(0x90c, 0x4);
    // Configure Streamer (AXI Side):
    write_csr(0x90d, (unsigned long)axi_src_data);
    // 4 Temporal strides:
    write_csr(0x90e, 0x0);
    write_csr(0x90f, 0x0);
    write_csr(0x910, 0x0);
    write_csr(0x911, 0x200);
    // 4 Temporal bounds:
    write_csr(0x912, 0x0);
    write_csr(0x913, 0x0);
    write_csr(0x914, 0x0);
    write_csr(0x915, 0x1);
    // Set direction:
    write_csr(0x916, 0x0);
    // Set start:
    write_csr(0x917, 0x1);
    // Await start:
    read_csr(0x917);
    LOG_VERBOSE("DMA done\n");
    LOG_VERBOSE("TCDM values:\n");
    int *tcdm_dest_data = (int *)TCDM_ADDR;
    for (int i = 0; i < TEST_SIZE; i++) {
      LOG_VERBOSE("  [%d] %p : 0x%08x\n", i, &tcdm_dest_data[i],
                  tcdm_dest_data[i]);
    }
  }
  cluster_sync();

  // --- PHASE 4: TCDM -> AXI (New Destination) ---
  if (hart == 2) {
    // Source: TCDM
    write_csr(0x900, TCDM_ADDR);

    // Dest: New AXI Location
    write_csr(0x90d, (unsigned long)axi_dest_data);

    write_csr(0x916, 0x1); // Direction: TCDM -> AXI
    write_csr(0x917, 0x1); // Start
    read_csr(0x917);
    LOG_VERBOSE("DMA Double-Transfer Complete.\n");
  }
  cluster_sync();

  // --- PHASE 5: Core 2 Validation ---
  if (hart == 1) {
    LOG_VERBOSE("Validating Final Results at %p...\n", axi_dest_data);

    for (int i = 0; i < TEST_SIZE; i++) {
      if (axi_dest_data[i] != axi_src_data[i]) {
        LOG_VERBOSE(
            "  ERROR: Mismatch at index %d! Expected 0x%08x, Got 0x % 08x\n ",
            i, axi_src_data[i], axi_dest_data[i]);
        fail_count++;
      } else {
        LOG_VERBOSE("  [%d] OK: 0x%08x\n", i, axi_dest_data[i]);
      }
    }

    if (fail_count == 0) {
      LOG_VERBOSE("TEST PASSED!\n");
    } else {
      LOG_VERBOSE("TEST FAILED with %d errors.\n", fail_count);
    }
  }
  cluster_sync();

  // --- PHASE 6: Exit ---
  if (hart == 1) {
    // If fail_count is 0, simulation returns 0 (Success)
    // If fail_count > 0, simulation returns the error count
    htif_exit(fail_count);
  }

  return 0;
}

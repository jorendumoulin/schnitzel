// #include <runtime.h>
//
// int *values = {}
//
//     int main() {
//
//   int hart = hart_id();
//
//   if (hart == 0) {
//     // Configure Streamer (TCDM Side):
//     write_csr(0x900, 0x10000000);
//     // 4 Temporal strides:
//     write_csr(0x901, 0x0);
//     write_csr(0x902, 0x0);
//     write_csr(0x903, 0x0);
//     write_csr(0x904, 0x200);
//     // 4 Temporal bounds:
//     write_csr(0x905, 0x0);
//     write_csr(0x906, 0x0);
//     write_csr(0x907, 0x0);
//     write_csr(0x908, 0x8);
//     // 3 Spatial strides:
//     write_csr(0x909, 0x20);
//     write_csr(0x90a, 0x10);
//     write_csr(0x90b, 0x8);
//     // Configure Streamer (AXI Side):
//     write_csr(0x90c, 0x20000);
//     // 4 Temporal strides:
//     write_csr(0x90d, 0x0);
//     write_csr(0x90e, 0x0);
//     write_csr(0x90f, 0x0);
//     write_csr(0x910, 0x200);
//     // 4 Temporal bounds:
//     write_csr(0x911, 0x0);
//     write_csr(0x912, 0x0);
//     write_csr(0x913, 0x0);
//     write_csr(0x914, 0x8);
//     // Set direction:
//     write_csr(0x915, 0x0);
//     // Set start:
//     write_csr(0x916, 0x1);
//     // Await start:
//     read_csr(0x916);
//   }
//   cluster_sync();
//
//   // Exit with code 0
//   htif_exit(0);
//   return 0;
// }

#include <runtime.h>

// Assuming your TCDM and AXI base addresses
#define TCDM_ADDR 0x10000000
#define AXI_DST_ADDR 0x80002000 // A different spot in L3
#define TEST_SIZE 8

// Global test data (Linker puts this in AXI/L3)
int src_data[TEST_SIZE] = {0xDEAD, 0xBEEF, 0xCAFE, 0xBABE,
                           0x1234, 0x5678, 0xAAAA, 0x5555};

int main() {
  int hart = hart_id();
  static int fail_count = 0; // Static so it persists across syncs

  // --- PHASE 1: Initialization ---
  if (hart == 1) {
    printf("Starting DMA Loopback Test: AXI -> TCDM -> AXI_NEW\n");
  }
  cluster_sync();

  // --- PHASE 2: Core 2 Prints Initial State ---
  if (hart == 1) {
    // printf("Initial AXI Source Values:\n");
    for (int i = 0; i < TEST_SIZE; i++) {
      // printf("  [%d] %p : 0x%08x\n", i, &src_data[i], src_data[i]);
    }
  }
  cluster_sync();

  // --- PHASE 3: AXI -> TCDM ---
  if (hart == 2) {
    // Source: AXI
    // printf("Setting up DMA:\n");
    write_csr(0x90c, (unsigned long)src_data);
    write_csr(0x910, sizeof(int)); // 4-byte stride
    write_csr(0x914, TEST_SIZE);

    // Dest: TCDM
    write_csr(0x900, TCDM_ADDR);
    write_csr(0x904, sizeof(int));
    write_csr(0x908, TEST_SIZE);

    write_csr(0x915, 0x0); // Direction: AXI -> TCDM
    write_csr(0x916, 0x1); // Start
    // printf("Await DMA:\n");
    read_csr(0x916); // Barrier for streamer completion
    printf("DMA done\n");
  }
  cluster_sync();

  // --- PHASE 4: TCDM -> AXI (New Destination) ---
  if (hart == 2) {
    // Source: TCDM
    write_csr(0x900, TCDM_ADDR);

    // Dest: New AXI Location
    write_csr(0x90c, AXI_DST_ADDR);

    write_csr(0x915, 0x1); // Direction: TCDM -> AXI
    write_csr(0x916, 0x1); // Start
    read_csr(0x916);
    printf("DMA Double-Transfer Complete.\n");
  }
  cluster_sync();

  // --- PHASE 5: Core 2 Validation ---
  if (hart == 1) {
    int *final_results = (int *)AXI_DST_ADDR;
    printf("Validating Final Results at %p...\n", final_results);

    for (int i = 0; i < TEST_SIZE; i++) {
      if (final_results[i] != src_data[i]) {
        printf(
            "  ERROR: Mismatch at index %d! Expected 0x%08x, Got 0x % 08x\n ",
            i, src_data[i], final_results[i]);
        fail_count++;
      } else {
        printf("  [%d] OK: 0x%08x\n", i, final_results[i]);
      }
    }

    if (fail_count == 0) {
      printf("TEST PASSED!\n");
    } else {
      printf("TEST FAILED with %d errors.\n", fail_count);
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

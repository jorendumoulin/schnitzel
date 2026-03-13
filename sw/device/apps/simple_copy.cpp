#include <memref.hpp>
#include <runtime.h>

constexpr int N = 16;

// Source data in AXI/L3 memory (64-byte aligned for 512-bit AXI bus)
alignas(64) int32_t src_data[N] = {1, 2,  3,  4,  5,  6,  7,  8,
                                   9, 10, 11, 12, 13, 14, 15, 16};

// TCDM destination buffer
TCDM int32_t dst_data[N];

// Program DMA to copy N int32s from AXI src to TCDM dst
void dma_copy(int32_t *tcdm_addr, int32_t *axi_addr) {
  // TCDM streamer: 4 temporal dims, spatial unroll (2,2,2,2)=16 ports
  write_csr(0x900, (unsigned long)tcdm_addr);
  // Temporal strides (only dim 0 used):
  write_csr(0x901, 0x0);
  write_csr(0x902, 0x0);
  write_csr(0x903, 0x0);
  write_csr(0x904, 0x200);
  // Temporal bounds (1 iteration covers all 16 elements spatially):
  write_csr(0x905, 0x0);
  write_csr(0x906, 0x0);
  write_csr(0x907, 0x0);
  write_csr(0x908, 0x1);
  // Spatial strides (2,2,2,2 unrolling → 16 contiguous 4-byte words):
  write_csr(0x909, 0x20);
  write_csr(0x90a, 0x10);
  write_csr(0x90b, 0x8);
  write_csr(0x90c, 0x4);

  // AXI streamer: 4 temporal dims, no spatial unroll (512-bit wide bus)
  write_csr(0x90d, (unsigned long)axi_addr);
  write_csr(0x90e, 0x0);
  write_csr(0x90f, 0x0);
  write_csr(0x910, 0x0);
  write_csr(0x911, 0x200);
  write_csr(0x912, 0x0);
  write_csr(0x913, 0x0);
  write_csr(0x914, 0x0);
  write_csr(0x915, 0x1);

  // Direction: AXI -> TCDM
  write_csr(0x916, 0x0);
  // Start and wait for completion
  write_csr(0x917, 0x1);
  read_csr(0x917);
}

// Hand-written equivalent of what snaxc should generate for memref.copy
void simple_copy(Memref<int32_t, 1> &src, Memref<int32_t, 1> &dst) {
  dma_copy(dst.aligned_data, src.aligned_data);
}

int main() {
  int hart = hart_id();

  // Set up memref descriptors (mirrors MLIR calling convention)
  Memref<int32_t, 1> src = {src_data, src_data, 0, {N}, {1}};
  Memref<int32_t, 1> dst = {dst_data, dst_data, 0, {N}, {1}};

  if (hart == 1) {
    verbose_printf("=== Simple Copy Test ===\n");
    verbose_printf("src: %p (AXI), dst: %p (TCDM)\n", src.aligned_data,
                   dst.aligned_data);
  }
  cluster_sync();

  // DMA core performs the copy
  if (hart == 2) {
    simple_copy(src, dst);
    verbose_printf("DMA copy done.\n");
  }
  cluster_sync();

  // Verify results
  if (hart == 1) {
    int nerr = 0;
    for (int i = 0; i < N; i++) {
      if (dst.aligned_data[i] != src.aligned_data[i]) {
        verbose_printf("  ERROR at [%d]: expected %d, got %d\n", i,
                       src.aligned_data[i], dst.aligned_data[i]);
        nerr++;
      } else {
        verbose_printf("  [%d] OK: %d\n", i, dst.aligned_data[i]);
      }
    }
    if (nerr == 0) {
      printf("TEST PASSED!\n");
    } else {
      printf("TEST FAILED with %d errors.\n", nerr);
    }
    htif_exit(nerr);
  }
  cluster_sync();
  htif_exit(0);
}

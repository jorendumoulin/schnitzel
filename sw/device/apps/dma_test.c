#include <runtime.h>

int main() {

  int hart = hart_id();

  if (hart == 0) {

    // Configure Streamer:
    write_csr(0x900, 0x10000000);
    // 4 Temporal strides:
    write_csr(0x901, 0x0);
    write_csr(0x902, 0x0);
    write_csr(0x903, 0x0);
    write_csr(0x904, 0x200);
    // 4 Temporal bounds:
    write_csr(0x905, 0x0);
    write_csr(0x906, 0x0);
    write_csr(0x907, 0x0);
    write_csr(0x908, 0x8);

    // 3 Spatial strides:
    write_csr(0x909, 0x20);
    write_csr(0x90a, 0x10);
    write_csr(0x90b, 0x8);

    // Configure Streamer:
    write_csr(0x90c, 0x20000);

    // 4 Temporal strides:
    write_csr(0x90d, 0x0);
    write_csr(0x90e, 0x0);
    write_csr(0x90f, 0x0);
    write_csr(0x910, 0x200);

    // 4 Temporal bounds:
    write_csr(0x911, 0x0);
    write_csr(0x912, 0x0);
    write_csr(0x913, 0x0);
    write_csr(0x914, 0x8);

    // Set direction:
    write_csr(0x915, 0x0);

    // Set start:
    write_csr(0x916, 0x1);

    // Await start:
    read_csr(0x916);
  }

  cluster_sync();

  // Exit with code 0
  htif_exit(0);
  return 0;
}

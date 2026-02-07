#include <runtime.h>

int main() {

  int hart = hartid();

  if (hart == 0) {
    unsigned long csr;
    unsigned long value;

    // Configure Streamer:
    csr = 0x900;
    value = 0x10000000;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    // 4 Temporal strides:
    csr = 0x901;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x902;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x903;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x904;
    value = 0x200;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    // 4 Temporal bounds:
    csr = 0x905;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x906;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x907;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x908;
    value = 0x8;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    // 3 Spatial strides:
    csr = 0x909;
    value = 0x20;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x90a;
    value = 0x10;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x90b;
    value = 0x8;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    // Configure Streamer:
    csr = 0x90c;
    value = 0x20000;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    // 4 Temporal strides:
    csr = 0x90d;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x90e;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x90f;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x910;
    value = 0x200;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    // 4 Temporal bounds:
    csr = 0x911;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x912;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x913;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    csr = 0x914;
    value = 0x8;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    // Set direction:
    csr = 0x915;
    value = 0x0;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    // Set start:
    csr = 0x916;
    value = 0x1;
    __asm__ volatile("csrw %0, %1" ::"i"(csr), "rK"(value));

    // Await start:
    csr = 0x916;
    __asm__ volatile("csrr %0, %1" : "=r"(value) : "i"(csr));
  }

  cluster_sync();

  // Exit with code 0
  htif_exit(0);
  return 0;
}

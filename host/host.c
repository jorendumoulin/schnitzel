#include <float.h>
#include <stddef.h>
#include <stdint.h>

#define N 10

uint32_t arr[N];

int main() {

  unsigned long value = 17;

#define write_csr(reg, val) ({ asm volatile("csrw %0, %1" ::"rK"(val)); })

  unsigned long csr = 0x300; // Example CSR address (mstatus)
  //__asm__ volatile ("csrr %0, %1" : "=r" (value) : "i" (csr));
  unsigned long mstatus;
  // asm volatile ("csrr %0, mstatus" : "=r"(mstatus));
  // mstatus |= (3UL << 13);   // FS = 11 (Dirty) asm volatile ("csrw mstatus,
  // %0" :: "r"(mstatus));

  // float a = 3.14;
  // float b = 3.45;
  // float c = a + b;

  for (size_t i = 0; i < N; i++)
    arr[i] = i;

  // asm volatile("cbo.flush (%0)" ::"r"(arr) : "memory");

  csr = 0x900; // Example CSR address (mstatus)
  //__asm__ volatile ("csrr %0, %1" : "=r" (value) : "i" (csr));

  return 0;
}

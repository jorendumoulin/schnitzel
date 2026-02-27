#include <runtime.h>

int main() {
  printf("Hello World! %d\n", 1);

  unsigned long value = 17;
  printf("value starts at %lu\n", value);

  unsigned long csr = 0x300; // Example CSR address (mstatus)
  value = read_csr(csr);
  printf("mstatus is at %lu\n", value);

  csr = 0x900; // Example CSR address (mstatus)
  value = read_csr(csr);
  printf("custom csr is at %lu\n", value);
  printf("Hello World! %d\n", 2);

  // Exit with code 0
  htif_exit(0);
  return 0;
}

#include <runtime.h>

int main() {
    printf("Hello World! %d\n", 1);
    printf("Hello World! %d\n", 2);


    unsigned long value = 17;
    printf("value starts at %lu\n", value);

    unsigned long csr = 0x300; // Example CSR address (mstatus)
    __asm__ volatile ("csrr %0, %1" : "=r" (value) : "i" (csr));
    printf("msatus is at %lu\n", value);

    csr = 0x900; // Example CSR address (mstatus)
    __asm__ volatile ("csrr %0, %1" : "=r" (value) : "i" (csr));
    printf("msatus is at %lu\n", value);

    printf("Hello World! %d\n", 2);

    // Exit with code 0
    htif_exit(0);
    return 0;
}

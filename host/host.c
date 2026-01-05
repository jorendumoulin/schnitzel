
int main() {

    unsigned long value = 17;

    #define write_csr(reg, val) ({ \
      asm volatile ("csrw %0, %1" :: "rK"(val)); })

    unsigned long csr = 0x300; // Example CSR address (mstatus)
    //__asm__ volatile ("csrr %0, %1" : "=r" (value) : "i" (csr));

    csr = 0x900; // Example CSR address (mstatus)
    //__asm__ volatile ("csrr %0, %1" : "=r" (value) : "i" (csr));

    return 0;
}

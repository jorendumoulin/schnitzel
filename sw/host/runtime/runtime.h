#include <stdint.h>

volatile uint32_t global_sync_reg
    __attribute__((section(".global_sync"), used));

// Write to synchronization register
void global_sync() { global_sync_reg = 42; };

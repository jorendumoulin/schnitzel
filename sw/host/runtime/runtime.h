#include <stdint.h>

volatile uint32_t global_sync __attribute__((section(".global_sync"), used));

// Write to synchronization register
void sync_global() { global_sync = 42; };

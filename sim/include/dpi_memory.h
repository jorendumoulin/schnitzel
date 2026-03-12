#ifndef __DPI_MEMORY_H
#define __DPI_MEMORY_H

#include "dynamic_memory.h"
#include <cstdint>

extern DynamicMemory g_dpi_memory;

#ifdef __cplusplus
extern "C" {
#endif

void dpi_memory_init();
void dpi_memory_load_program(const char *path);
void dpi_set_host_addresses(uint32_t tohost, uint32_t fromhost);
bool dpi_check_host_exit();
void dpi_set_exit(bool exit);
uint32_t dpi_get_tohost_addr();
uint32_t dpi_get_fromhost_addr();

#ifdef __cplusplus
}
#endif

#endif

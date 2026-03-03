#include "dpi_memory.h"
#include "loader.h"
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <svdpi.h>

DynamicMemory g_dpi_memory(4096);
static Loader g_loader;
static uint32_t g_tohost_addr = 0;
static uint32_t g_fromhost_addr = 0;
static bool g_exit_requested = false;

extern "C" {

void dpi_mem_read_512(uint32_t addr, uint32_t *data) {
  g_dpi_memory.read_chunk(addr, 64, data);
}

void dpi_mem_write_512(uint32_t addr, uint32_t *data, uint32_t *ben) {

  uint64_t strobe = 0;
  memcpy(&strobe, ben, 8);

  alignas(8) uint8_t current[64], wdata[64];
  g_dpi_memory.read_chunk(addr, 64, current);
  memcpy(wdata, data, 64);

  for (int i = 0; i < 64; i++) {
    if (strobe & (1ULL << i)) {
      current[i] = wdata[i];
    }
  }
  g_dpi_memory.write_chunk(addr, 64, current);

  if (addr <= g_tohost_addr && g_tohost_addr < addr + 64) {
    extern void dpi_handle_host();
    dpi_handle_host();
  }
}

void dpi_mem_read_64(uint32_t addr, svBitVecVal *data) {
  g_dpi_memory.read_chunk(addr, 8, data);
}

void dpi_mem_write_64(uint32_t addr, const svBitVecVal *data,
                      const svBitVecVal *ben) {
  uint8_t strobe = 0;
  memcpy(&strobe, ben, 1);

  alignas(8) uint8_t current[8], wdata[8];
  g_dpi_memory.read_chunk(addr, 8, current);
  memcpy(wdata, data, 8);

  for (int i = 0; i < 8; i++) {
    if (strobe & (1 << i)) {
      current[i] = wdata[i];
    }
  }
  g_dpi_memory.write_chunk(addr, 8, current);
  ;

  if (addr <= g_tohost_addr && g_tohost_addr < addr + 8) {
    extern void dpi_handle_host();
    dpi_handle_host();
  }
}
}

extern "C" {

void dpi_memory_init() { g_exit_requested = false; }

void dpi_memory_load_program(const char *path) {
  g_loader.load_program(path, g_dpi_memory);
  dpi_set_host_addresses(g_loader.get_tohost(), g_loader.get_fromhost());
}

void dpi_set_host_addresses(uint32_t tohost, uint32_t fromhost) {
  g_tohost_addr = tohost;
  g_fromhost_addr = fromhost;
}

bool dpi_check_host_exit() { return g_exit_requested; }

void dpi_set_exit(bool exit) { g_exit_requested = exit; }

uint32_t dpi_get_tohost_addr() { return g_tohost_addr; }

uint32_t dpi_get_fromhost_addr() { return g_fromhost_addr; }
}

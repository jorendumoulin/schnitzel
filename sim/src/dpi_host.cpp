#include "dpi_memory.h"
#include <cstdio>
#include <cstring>

extern "C" {

void dpi_handle_host() {
  extern uint32_t dpi_get_tohost_addr();
  extern uint32_t dpi_get_fromhost_addr();
  extern void dpi_set_exit(bool);

  uint32_t tohost_addr = dpi_get_tohost_addr();
  uint32_t tohost = g_dpi_memory.read_word(tohost_addr);
  if (tohost == 0)
    return;

  uint32_t syscall_mem[8];
  for (int i = 0; i < 8; i++) {
    syscall_mem[i] = g_dpi_memory.read_word(tohost + i * 4);
  }

  char putc_buffer[256];
  uint32_t fromhost_addr = dpi_get_fromhost_addr();

  switch (syscall_mem[0]) {
  case 64:
    g_dpi_memory.read_chunk(syscall_mem[2], syscall_mem[3], putc_buffer);
    printf("(hart %d) %.*s", syscall_mem[4], syscall_mem[3], putc_buffer);
    fflush(stdout);
    g_dpi_memory.write_word(tohost_addr, 0);
    g_dpi_memory.write_word(fromhost_addr, 1);
    break;
  case 93:
    dpi_set_exit(true);
    g_dpi_memory.write_word(tohost_addr, 0);
    break;
  default:
    fprintf(stderr, "Unknown syscall: %d\n", syscall_mem[0]);
    g_dpi_memory.write_word(tohost_addr, 0);
    g_dpi_memory.write_word(fromhost_addr, 1);
    break;
  }
}
}

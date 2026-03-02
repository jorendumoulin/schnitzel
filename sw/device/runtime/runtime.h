#ifndef RUNTIME_H
#define RUNTIME_H

#include <stddef.h>

void putchar_(char ch);
void htif_exit(int exit_code);
int hart_id();
void global_sync() { __asm__ volatile("csrr x0, 0x800"); }
void cluster_sync() { __asm__ volatile("csrr x0, 0x810"); }

int printf(const char *format, ...);

void *memset(void *s, int c, size_t n) {
  unsigned char *p = s;
  while (n--) {
    *p++ = (unsigned char)c;
  }
  return s;
}

#endif

#ifndef RUNTIME_H
#define RUNTIME_H

#include <stddef.h>

void putchar_(char ch);
void htif_exit(int exit_code);

int printf_(const char *format, ...);
#define printf printf_

void *memset(void *s, int c, size_t n) {
  unsigned char *p = s;
  while (n--) {
    *p++ = (unsigned char)c;
  }
  return s;
}

#endif

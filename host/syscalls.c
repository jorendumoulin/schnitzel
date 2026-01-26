#include <sys/types.h>

extern void putchar_(char ch);

int _write(int fd, const void *buf, size_t count) {
  const char *c = buf;
  for (size_t i = 0; i < count; i++) {
    putchar_(c[i]);
    // send c[i] to your UART / MMIO / simulator
    // example:
    // UART_TX = c[i];
  }
  return count;
}

void _exit(int code) {
  // signal exit to simulator or halt CPU
  while (1) {
    asm volatile("wfi");
  }
}

void *_sbrk(ptrdiff_t incr) {
  extern char _end;
  static char *heap_end;

  if (!heap_end)
    heap_end = &_end;

  char *prev = heap_end;
  heap_end += incr;
  return prev;
}

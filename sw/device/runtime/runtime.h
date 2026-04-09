#ifndef RUNTIME_H
#define RUNTIME_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

void putchar_(char ch);
void htif_exit(int exit_code);
int hart_id();
void global_sync() { __asm__ volatile("csrr x0, 0x800"); }
void cluster_sync() { __asm__ volatile("csrr x0, 0x810"); }

int printf(const char *format, ...);

void *memset(void *s, int c, size_t n) {
  unsigned char *p = (unsigned char *)s;
  while (n--) {
    *p++ = (unsigned char)c;
  }
  return s;
}

void *memcpy(void *dest, const void *src, size_t n) {
  unsigned char *d = (unsigned char *)dest;
  const unsigned char *s = (const unsigned char *)src;
  while (n--) {
    *d++ = *s++;
  }
  return dest;
}

// --- Helper Macros ---
#define TCDM __attribute__((section(".tcdm"), aligned(64)))

#define write_csr(reg, val)                                                    \
  ({ __asm__ volatile("csrw %0, %1" ::"i"(reg), "rK"(val)); })

#define read_csr(reg)                                                          \
  ({                                                                           \
    unsigned long __v;                                                         \
    __asm__ volatile("csrr %0, %1" : "=r"(__v) : "i"(reg));                    \
    __v;                                                                       \
  })

#ifdef __cplusplus
}
#endif

#ifdef VERBOSE
#define verbose_printf(...) printf(__VA_ARGS__)
#else
#define verbose_printf(...) ((void)0)
#endif

#endif

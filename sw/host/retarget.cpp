#include <stdio.h>
#include <unistd.h>

// 1. Your hardware-specific function
extern void putchar_(char ch);

static int riscv_putc(char c, FILE *file) {
  (void)file;
  putchar_(c);
  return (unsigned char)c;
}

static int riscv_getc(FILE *file) {
  (void)file;
  return -1; // EOF
}

// 2. Initialize the FILE structure manually to bypass the missing macro
// This matches the FDEV_SETUP_STREAM layout
static FILE __my_stdio = {
    .flags = 0x0002 | 0x0001, // _FDEV_SETUP_READ | _FDEV_SETUP_WRITE (or
                              // similar Picolibc internal)
    .put = riscv_putc,
    .get = riscv_getc,
    .flush = NULL};

// 3. Picolibc uses these specific global pointers
// We define the actual pointers the library looks for
FILE *const __stdin = &__my_stdio;
FILE *const __stdout = &__my_stdio;
FILE *const __stderr = &__my_stdio;

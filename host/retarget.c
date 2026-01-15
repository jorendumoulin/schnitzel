#include "stdio_private.h"
#include <stdio.h>

// 1. Declare your existing hardware-specific function
extern void putchar_(char ch);

// 2. Create the bridge function
// The library expects (char, FILE*), but your putchar_ only takes (char)
static int low_level_putc(char c, FILE *stream) {
  (void)stream; // The stream pointer isn't needed for simple HTIF output
  putchar_(c);
  return (unsigned char)c;
}

// 3. Define the internal FILE structure
// We initialize the inner 'file' struct with our function pointer and the Write
// flag (__SWR)
static struct __file_str __my_stdout_str = {
    .file =
        {
            .unget = 0,
            .flags = __SWR, // Status: Write-only
            .put = low_level_putc,
            .get = NULL, // No input supported on this stream
            .flush = NULL
#ifdef __STDIO_LOCKING
                         .lock =
                __LOCK_NONE, // Disable locking if not in a multi-threaded OS
#endif
        },
    .pos = NULL,
    .end = NULL,
    .size = 0,
    .alloc = false};

// 4. Export the global stdout pointer
// This is the variable that puts.c and printf() look for at link-time
FILE *const stdout = &__my_stdout_str.file;

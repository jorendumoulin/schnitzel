#include <errno.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>

extern void putchar_(char ch);

// Heap management
extern char _end;
static char *heap_ptr = &_end;

void *_sbrk(int incr) {
  char *prev_heap = heap_ptr;
  heap_ptr += incr;
  return (void *)prev_heap;
}

int _gettimeofday(struct timeval *tv, void *tz) {
  if (tv) {
    tv->tv_sec = 42;
    tv->tv_usec = 0;
  }
  return 0;
}

// File status - mark stdout/stderr as character devices
int _fstat(int file, struct stat *st) {
  st->st_mode = S_IFCHR;
  return 0;
}

// Close file - for bare metal, just succeed
int _close(int file) { return 0; }

// Seek - not supported in bare metal console I/O
int _lseek(int file, int offset, int whence) {
  errno = ESPIPE; // Illegal seek
  return -1;
}

int __wrap__write(int file, char *ptr, int len) {
  if (file == 1 || file == 2) {
    for (int i = 0; i < len; i++) {
      putchar_(ptr[i]);
    }
    return len;
  }
  errno = EBADF;
  return -1;
}

/*
 * _read: Reads from standard input
 */
int _read(int file, char *ptr, int len) {
  if (file == 0) { // stdin
    // For now, mirroring your riscv_getc logic: return EOF/0
    return 0;
  }
  errno = EBADF;
  return -1;
}

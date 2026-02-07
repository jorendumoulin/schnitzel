#include <stddef.h>
#include <stdint.h>

// Number of hardware threads (harts) the program will use.
// TODO: replace with parametrized number of harts
#ifndef NUM_HARTS
#define NUM_HARTS 3
#endif

// Putchar buffer size per hart.
#define PUTC_BUFFER_LEN 256

// hart_id helper
int hart_id() {
  int result;
  __asm__ volatile("csrr %0, mhartid" : "=r"(result));
  return result;
};

// Statically allocated tohost and fromhost pointers,
// shared between host, devices and simulation
volatile uint32_t tohost __attribute__((section(".tohost"), used));
volatile uint32_t fromhost __attribute__((section(".fromhost"), used));

struct putc_buffer_hdr {
  size_t size;             /* current number of bytes in data[] */
  uint32_t syscall_mem[8]; /* syscall descriptor used by host when flushing */
};

// Allocate a putchar buffer for each of the harts in the system.
struct putc_buffer {
  struct putc_buffer_hdr hdr;
  char data[PUTC_BUFFER_LEN];
};

// Important that this static buffer is statically allocated in DRAM: otherwise
// it may end up in the stack (TCDM) and the host may not have direct access.
static struct putc_buffer putc_buffers[NUM_HARTS];

// Flush the putchar buffer: this function sends a signal to the simulator host
// to print the characters in the putchar buffer and clears the buffer.
static void flush_buffer(struct putc_buffer *buf) {

  struct putc_buffer_hdr *h = &buf->hdr;

  if (h->size == 0) {
    return;
  }

  int hart = hart_id();

  /* Prepare an HTIF-style "write" syscall */
  h->syscall_mem[0] = 64;                   /* syscall: write */
  h->syscall_mem[1] = 1;                    /* fd = stdout */
  h->syscall_mem[2] = (uintptr_t)buf->data; /* pointer to data */
  h->syscall_mem[3] = h->size;              /* length */
  h->syscall_mem[4] = hart;                 /* hart id */

  // Keep sending a request to the host until it has read the request.
  while (1) {
    // Trigger the host by writing the pointer to syscall_mem into tohost
    tohost = (uintptr_t)h->syscall_mem;
    // Busy-wait for host response
    while (fromhost == 0)
      ;
    /* Make sure the response is targeted at this hartid */
    // TODO: be sure to only break here when the response is correct,
    // otherwise send the signal again
    break;
  }

  /* Reset the host signal and our buffer */
  fromhost = 0;
  h->size = 0;
}

// Main putchar_ function: this stores a character in the putchar buffer,
// and flushes the buffer if it is full or on a '\n' character.
void putchar_(char ch) {

  // Get the correct putc buffer
  unsigned int hart = hart_id();
  struct putc_buffer *buf = &putc_buffers[hart];
  struct putc_buffer_hdr *h = &buf->hdr;

  // Append the character
  buf->data[h->size++] = ch;

  // Flush on newline or when full
  if (ch == '\n' || h->size >= sizeof(buf->data)) {
    flush_buffer(buf);
  }
}

// Allocate a single exit syscall for all harts in the system: as soon as a
// single hart exits, the simulation stops.
// TODO: better behaviour here would be to assert every hart in the system
// should exit before finishing the simulation.
static uint64_t exit_syscall[4];

// HTIF exit routine
void htif_exit(int code) {
  exit_syscall[0] = 93; /* exit */
  exit_syscall[1] = (uint64_t)code;
  tohost = (uintptr_t)exit_syscall;
  while (fromhost == 0) {
  }
  fromhost = 0;
}

#include <stdint.h>
#include <stddef.h>

// Number of hardware threads (harts) the program will use.
#ifndef NUM_HARTS
#define NUM_HARTS 2 // TODO: replace with actual number of harts if available
#endif

// Putchar buffer size per hart.
#define PUTC_BUFFER_LEN 256

int hartid() {
    int result;
    __asm__ volatile ("csrr %0, mhartid" : "=r" (result) );
    return result;
};

void cluster_sync() {
    __asm__ volatile ("csrr x0, 0x800");
};

volatile uintptr_t tohost __attribute__((section(".tohost"), used));
volatile uintptr_t fromhost __attribute__((section(".fromhost"), used));

struct putc_buffer_hdr {
    size_t size;            /* current number of bytes in data[] */
    uint32_t syscall_mem[8];/* syscall descriptor used by host when flushing */
};

/* Putchar buffers */
struct putc_buffer {
    struct putc_buffer_hdr hdr;
    char data[PUTC_BUFFER_LEN];
};

// Important that this static buffer is statically allocated in DRAM: otherwise host has no direct access.
static struct putc_buffer putc_buffers[NUM_HARTS];

/* ---------- Helper: flush one buffer via HTIF ---------- */

static void flush_buffer(struct putc_buffer *buf)
{
    struct putc_buffer_hdr *h = &buf->hdr;

    if (h->size == 0) {
        return;
    }

    int hart = hartid();

    /* Prepare an HTIF-style "write" syscall */
    h->syscall_mem[0] = 64;                     /* syscall: write */
    h->syscall_mem[1] = 1;                      /* fd = stdout */
    h->syscall_mem[2] = (uintptr_t)buf->data;   /* pointer to data */
    h->syscall_mem[3] = h->size;                /* length */
    h->syscall_mem[4] = hart;      /* length */

    /* Trigger the host by writing the pointer to syscall_mem into tohost */
    tohost = (uintptr_t)h->syscall_mem;

    /* Busy-wait for host response */
    while (fromhost == 0);

    /* Reset the host signal and our buffer */
    fromhost = 0;
    h->size = 0;
}

void putchar_(char ch)
{
    unsigned int hart = hartid(); // TODO: replace with snrt_hartid() or equivalent

    struct putc_buffer *buf = &putc_buffers[hart];
    struct putc_buffer_hdr *h = &buf->hdr;

    // append character (no bounds check required; we handle full flush below)
    buf->data[h->size++] = ch;

    // flush on newline or when full
    if (ch == '\n' || h->size >= sizeof(buf->data)) {
        flush_buffer(buf);
    }
}

// Important that this static buffer is statically allocated in DRAM: otherwise host has no direct access.
static uint64_t exit_syscall[4];

// HTIF exit routine
void htif_exit(int code)
{
    exit_syscall[0] = 93;    /* exit */
    exit_syscall[1] = (uint64_t)code;
    tohost = (uintptr_t)exit_syscall;
    while (fromhost == 0) { }
    fromhost = 0;
}

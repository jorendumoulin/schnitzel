#include <stdint.h>
#include <stddef.h>

// Number of hardware threads (harts) the program will use.
#ifndef NUM_HARTS
#define NUM_HARTS 1 // TODO: replace with actual number of harts if available
#endif

// Putchar buffer size per hart.
#define PUTC_BUFFER_LEN 256

// HTIF communication registers
struct htif_regs {
    volatile uintptr_t tohost;
    volatile uintptr_t fromhost;
};

struct htif_regs htif __attribute__((section(".tohost")));

struct putc_buffer_hdr {
    size_t size;            /* current number of bytes in data[] */
    uint64_t syscall_mem[8];/* syscall descriptor used by host when flushing */
};

/* Putchar buffers */
struct putc_buffer {
    struct putc_buffer_hdr hdr;
    char data[PUTC_BUFFER_LEN];
};

static struct putc_buffer putc_buffers[NUM_HARTS];

/* ---------- Helper: flush one buffer via HTIF ---------- */

static void flush_buffer(struct putc_buffer *buf)
{
    struct putc_buffer_hdr *h = &buf->hdr;

    if (h->size == 0) {
        return;
    }

    /* Prepare an HTIF-style "write" syscall */
    h->syscall_mem[0] = 64;                     /* syscall: write */
    h->syscall_mem[1] = 1;                      /* fd = stdout */
    h->syscall_mem[2] = (uintptr_t)buf->data;   /* pointer to data */
    h->syscall_mem[3] = h->size;                /* length */

    /* Trigger the host by writing the pointer to syscall_mem into tohost */
    htif.tohost = (uintptr_t)h->syscall_mem;

    /* Busy-wait for host response */
    while (htif.fromhost == 0);

    /* Reset the host signal and our buffer */
    htif.fromhost = 0;
    h->size = 0;
}

void _putchar(char ch)
{
    unsigned int hart = 0; // TODO: replace with snrt_hartid() or equivalent

    struct putc_buffer *buf = &putc_buffers[hart];
    struct putc_buffer_hdr *h = &buf->hdr;

    // append character (no bounds check required; we handle full flush below)
    buf->data[h->size++] = ch;

    // flush on newline or when full
    if (ch == '\n' || h->size >= sizeof(buf->data)) {
        flush_buffer(buf);
    }
}

// HTIF exit routine
void htif_exit(int code)
{
    volatile uint64_t exit_syscall[4];
    exit_syscall[0] = 93;    /* exit */
    exit_syscall[1] = (uint64_t)code;
    htif.tohost = (uintptr_t)exit_syscall;
    while (htif.fromhost == 0) { }
    htif.fromhost = 0;
}

int main() {
    // Example usage of _putchar
    const char *message = "Hello, HTIF!\n";
    for (const char *p = message; *p != '\0'; p++) {
        _putchar(*p);
    }

    // Exit with code 0
    htif_exit(0);
    return 0;
}

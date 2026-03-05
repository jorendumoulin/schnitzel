#ifndef __HTIF_RUNTIME_H
#define __HTIF_RUNTIME_H

#ifdef __cplusplus
extern "C" {
#endif

// Prints a character to simulation output.
// Implementation buffers characters until the buffer is full
// or on the first newline ('\n')
void putchar_(char ch);

// HTIF exit routine
// Sends a signal to the simulator host to exit the simulation.
void htif_exit(int code);

#ifdef __cplusplus
}
#endif

#endif // __HTIF_RUNTIME_H

#ifndef __HTIF_RUNTIME_H
#define __HTIF_RUNTIME_H

// Prints a character to simulation output.
// Implementation buffers characters until the buffer is full
// or on the first newline ('\n')
void putchar_(char ch);

// HTIF exit routine
// Sends a signal to the simulator host to exit the simulation.
void htif_exit(int code);

#endif // __HTIF_RUNTIME_H

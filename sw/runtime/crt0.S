    .section .init
    .globl _start
_start:
    # Set up stack pointer
    la sp, _stack_top

    call main

    # Loop forever
hang:
    j hang

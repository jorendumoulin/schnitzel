    .section .init
    .globl _start
_start:

    # Set up stack pointer
    # Get hartid:
    csrr a0, mhartid
    # Each hart gets its own stack space of 2KB
    li a1, 0x800        # 2KB per hart
    mul a0, a0, a1      # hartid * 2KB
    la a1, _stack_top   # Load address of stack top
    sub sp, a1, a0      # Set sp = stack_top - (hartid * 2KB)

    call main

    # Loop forever
hang:
    j hang

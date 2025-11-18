    .section .init
    .globl _start
_start:
    # Set up stack pointer
    la sp, _stack_top

# The loader should zero bss?
#     # Zero .bss
#     la   t0, __bss_start
#     la   t1, __bss_end
#
# zero_bss:
#     beq  t0, t1, bss_done
#     sw   x0, 0(t0)
#     addi t0, t0, 4
#     j    zero_bss
# bss_done:

    # Call main()
    call main

    # Loop forever
hang:
    j hang

#.align 6; .global tohost; tohost: .dword 0;
#.align 6; .global fromhost; fromhost: .dword 0;

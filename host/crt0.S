.section .text.init
  .global _start
  .type   _start, @function

_start:
  .option push
  .option norelax
  /* 1. Initialize Stack and Global Pointer */
  la sp, _stack_top
  la gp, __global_pointer
  .option pop

  /* 2. Copy data from flash to ram */
  la a0, __data_start
  la a1, __data_source
  la a2, __data_size
  beqz a2, 1f                    # Skip if size is 0
  call memcpy

  /* 3. Enable FPU */
  li t0, 0x00006000
  csrs sstatus, t0
  csrs mstatus, t0
  fscsr x0
1:

  /* 3. Clear bss */
  la a0, __bss_start
  li a1, 0                       # Value (0) goes in a1
  la a2, __bss_size              # Size goes in a2
  beqz a2, 2f                    # Skip if size is 0
  call memset
2:

  /* 4. C/C++ inits */
  la   a0, __libc_fini_array
  call atexit
  call __libc_init_array

  /* 5. Jump to main */
  li   a0, 0                     # argc
  li   a1, 0                     # argv
  li   a2, 0                     # envp
  call main

  /* 6. Hang on exit */
hang:
  wfi                            # Optional: Sleep until an interrupt happens
  j hang

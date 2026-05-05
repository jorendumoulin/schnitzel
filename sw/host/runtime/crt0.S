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

  /* 4. Enable FPU */
  li t0, 0x00006000
  csrs mstatus, t0
  fscsr x0

  /* 6. C/C++ inits */
  la   a0, __libc_fini_array
  call atexit
  call __libc_init_array

  /* 7. Jump to main */
  li   a0, 0                     # argc
  li   a1, 0                     # argv
  li   a2, 0                     # envp
  call main

  /* 8. Hang on exit */
hang:
  wfi                            # Optional: Sleep until an interrupt happens
  j hang

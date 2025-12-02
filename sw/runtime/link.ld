MEMORY
{
  DRAM   (rwx): ORIGIN = 0x10000, LENGTH = 1024K
  TCDM   (rwx): ORIGIN = 0x10000000, LENGTH = 32K
}

SECTIONS
{
  . = ORIGIN(DRAM);

  .text : {
    *(.init*)
    *(.text*)
    *(.rodata*)
  } > DRAM

  .data : {
    *(.data*)
  } > DRAM

  .bss : {
    __bss_start = .;
    *(.bss*)
    *(COMMON)
    __bss_end = .;
  } > DRAM

  /* Stack top symbol */
  _stack_top = ORIGIN(TCDM) + LENGTH(TCDM);
}

MEMORY
{
  HTIF   (rwx): ORIGIN = 0x2000, LENGTH = 4K
  DRAM   (rwx): ORIGIN = 0x10080, LENGTH = 1024K
  TCDM   (rwx): ORIGIN = 0x10000000, LENGTH = 32K
}

SECTIONS
{
  /* Ibex seems to start at boot addr + 0x80 */
  . = ORIGIN(DRAM) + 0x80;

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

  /* HTIF communication */
  .tohost : ALIGN(8) {} > HTIF
  .fromhost : ALIGN(8) {} > HTIF

  .tcdm (NOLOAD) : {
    . = ALIGN(64);  /* Force the start of the section to be 64-byte aligned */
    *(.tcdm*)
    . = ALIGN(64);  /* Ensure the next section starts cleanly too */
  } > TCDM

  /* Stack top symbol */
  _stack_top = ORIGIN(TCDM) + LENGTH(TCDM);
}

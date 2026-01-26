ENTRY(_start)

MEMORY
{
    HTIF   (rwx): ORIGIN = 0x2000, LENGTH = 4K
    RAM    (rwx): ORIGIN = 0x60000000, LENGTH = 1024K
}

SECTIONS
{
    /* Start of RAM */
    . = ORIGIN(RAM);
    PROVIDE(__stack = ORIGIN(RAM) + LENGTH(RAM));

    .text : {
        *(.text.init)
        *(.text*)
    } > RAM

    .rodata : {
        *(.rodata*)
    } > RAM

    /* Flash copy of .data */
    .data_load : {
        __data_source = .;
        KEEP(*(.data*))   /* initial values stored in flash */
    } > RAM

    .data : AT(__data_source) {
        __data_start = .;
        *(.data*)
    } > RAM
    __data_size = SIZEOF(.data);

    .sdata : {
        __global_pointer$ = . + 0x800;
        *(.sdata*)
    } > RAM

    .bss : {
        __bss_start = .;
        *(.sbss*)
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    } > RAM
    __bss_size = __bss_end - __bss_start;

    .tdata : {
        *(.tdata*)
    } > RAM
    __tls_base = ADDR(.tdata);

    _end = .;

    /* HTIF communication */
    .tohost : ALIGN(8) {} > HTIF
    .fromhost : ALIGN(8) {} > HTIF
}

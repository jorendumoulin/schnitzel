set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_PROCESSOR riscv)

set(TOOLS /home/joren/Downloads/riscv)
set(CMAKE_C_COMPILER ${TOOLS}/bin/riscv64-unknown-elf-gcc)
set(CMAKE_CXX_COMPILER ${TOOLS}/bin/riscv64-unknown-elf-g++)
set(CMAKE_ASM_COMPILER ${TOOLS}/bin/riscv64-unknown-elf-gcc)
set(CMAKE_LINKER ${TOOLS}/bin/riscv64-unknown-elf-ld)

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD 17)


add_compile_options(
  "$<$<COMPILE_LANGUAGE:CXX>:-fno-unwind-tables;-fno-rtti;-fno-exceptions>"
  -fdata-sections -ffunction-sections
  -Wno-error=unterminated-string-initialization
)

add_link_options(--specs=nosys.specs)
add_link_options(LINKER:--nmagic,--gc-sections)

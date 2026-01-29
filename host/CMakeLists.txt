set(CMAKE_C_COMPILER   riscv64-unknown-elf-gcc)
set(CMAKE_CXX_COMPILER riscv64-unknown-elf-g++)

# Remove standard cmake flags
set(CMAKE_SHARED_LIBRARY_LINK_C_FLAGS "")
set(CMAKE_SHARED_LIBRARY_LINK_CXX_FLAGS "")

# Include paths for picolibc:
#if(PICOLIBC_PREFIX)
#  set(PICOLIBC_SYSROOT "${PICOLIBC_PREFIX}/picolibc/riscv64-unknown-elf")
#else()
#  set(PICOLIBC_SYSROOT "/usr/local/picolibc/riscv64-unknown-elf")
#endif()
set(PICOLIBC_PREFIX /home/josse/riscv/)
set(PICOLIBC_SYSROOT /home/josse/riscv/picolibc/riscv64-unknown-elf/)
include_directories(SYSTEM ${PICOLIBC_SYSROOT}/include)

# Default compile options
add_compile_options(
  -ftls-model=local-exec
  -mstack-protector-guard=global
)

# Library paths
link_directories(
  ${PICOLIBC_SYSROOT}/lib/${CMAKE_SYSTEM_PROCESSOR}
  ${PICOLIBC_SYSROOT}/lib
  ${CMAKE_SOURCE_DIR}/host
)

# libc/libgcc linker group:
link_libraries(
  -Wl,--start-group
  gcc
  c
  -Wl,--end-group
)

# Other link options:
add_link_options(
  -Tlink.ld
  -Wl,--gc-sections
  -nostartfiles
  -nostdlib
  ${PICOLIBC_SYSROOT}/lib/crt0.o
)

# Testing executable
add_executable(picolibc_test
  host.c
  test.c
  retarget.c
)

target_include_directories(picolibc_test PRIVATE
  ${CMAKE_SOURCE_DIR}/submodules/picolibc/libc/stdio
  ${PICOLIBC_SYSROOT}/include
  ${CMAKE_SOURCE_DIR}/submodules/picolibc/libc/include
  ${CMAKE_SOURCE_DIR}/submodules/picolibc/build-riscv64-unknown-elf/
)

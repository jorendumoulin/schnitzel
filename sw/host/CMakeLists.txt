cmake_minimum_required(VERSION 3.14)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../")

if(NOT CMAKE_TOOLCHAIN_FILE)
  set(CMAKE_TOOLCHAIN_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/runtime/cva6-toolchain.cmake"
    CACHE FILEPATH "Toolchain file")
endif()

project(host ASM C CXX)

add_library(host_runtime STATIC
  # start files
  ./runtime/crt0.S
  ./runtime/syscalls.c
  # putchar_ support via htif runtime:
  ${ROOT}/sw/common/htif/htif_runtime.c
)
target_link_options(host_runtime INTERFACE
    # Supply a custom startup and linker script:
    -T ${CMAKE_CURRENT_SOURCE_DIR}/runtime/link.ld
    -nostartfiles
    # Disable warning about load with rwx permisisons
    -Wl,--no-warn-rwx-segments
    # Overwrite newlib's _write stub:
    -Wl,--wrap=_write
    -Wl,--undefined=__wrap__write
)

add_subdirectory(apps)

# Set the runtime path
include("${TOOLCHAIN_ROOT}/riscv-toolchain.cmake")
set(RUNTIME_PATH "${CMAKE_SOURCE_DIR}/sw/runtime")

add_executable(hello_world.elf hello_world.c)
target_include_directories(hello_world.elf PRIVATE ${RUNTIME_PATH})
target_link_libraries(hello_world.elf PRIVATE runtime)

target_link_options(hello_world.elf PRIVATE
    -nostdlib
    -nostartfiles
    -fuse-ld=lld
    -T link.ld
    -L${RUNTIME_PATH}
)

# Everything in the sw/ directory is built using the RISC-V toolchain
include("${TOOLCHAIN_ROOT}/riscv-toolchain.cmake")

add_subdirectory(bootrom)

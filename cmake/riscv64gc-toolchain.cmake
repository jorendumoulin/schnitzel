cmake_minimum_required(VERSION 3.20)

set(PICOLIBC_SYSROOT "/usr/local/picolibc/riscv64-unknown-elf" CACHE PATH "Picolibc sysroot")
set(GCC_TOOLCHAIN "/home/joren/Downloads/riscv" CACHE PATH "GCC toolchain path")

set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR riscv64)

# Target and sysroot flags
add_compile_options(
    --target=riscv64-unknown-elf
    --sysroot=${PICOLIBC_SYSROOT}
    --gcc-toolchain=${GCC_TOOLCHAIN}
    -march=rv64gc
    -mabi=lp64d
)

# C++ specific flags
add_compile_options(
    $<$<COMPILE_LANGUAGE:CXX>:-fno-exceptions>
    $<$<COMPILE_LANGUAGE:CXX>:-fno-rtti>
    $<$<COMPILE_LANGUAGE:CXX>:-isystem${GCC_TOOLCHAIN}/riscv64-unknown-elf/include/c++/15.2.0>
    $<$<COMPILE_LANGUAGE:CXX>:-isystem${GCC_TOOLCHAIN}/riscv64-unknown-elf/include/c++/15.2.0/riscv64-unknown-elf>
)

add_link_options(
    --target=riscv64-unknown-elf
    --sysroot=${PICOLIBC_SYSROOT}
    --gcc-toolchain=${GCC_TOOLCHAIN}
    -march=rv64gc
    -mabi=lp64d
    -nostdlib
    -nostartfiles
    -L{$PICOLIBC_SYSROOT}/lib
    -L{$GCC_TOOLCHAIN}/lib/gcc/riscv64-unknown-elf/15.2.0
)

# Skip compiler tests - they fail because we don't have a complete C library yet
# set(CMAKE_C_COMPILER_WORKS 1)
# set(CMAKE_CXX_COMPILER_WORKS 1)

# # Or alternatively, configure the test to work with picolibc
# set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
#
# # Common flags
# set(COMMON_FLAGS "--target=riscv64-unknown-elf --sysroot=${PICOLIBC_SYSROOT} --gcc-toolchain=${GCC_TOOLCHAIN} -march=rv64gc -mabi=lp64d")
#
# set(CMAKE_C_FLAGS_INIT "${COMMON_FLAGS}")
# set(CMAKE_CXX_FLAGS_INIT "${COMMON_FLAGS} -fno-exceptions -fno-rtti")
#
# # C++ include paths
# set(CMAKE_CXX_FLAGS_INIT "${CMAKE_CXX_FLAGS_INIT} -isystem${GCC_TOOLCHAIN}/riscv64-unknown-elf/include/c++/15.2.0")
# set(CMAKE_CXX_FLAGS_INIT "${CMAKE_CXX_FLAGS_INIT} -isystem${GCC_TOOLCHAIN}/riscv64-unknown-elf/include/c++/15.2.0/riscv64-unknown-elf")
#
# # Linker flags
# set(CMAKE_EXE_LINKER_FLAGS_INIT "${COMMON_FLAGS}")
#
# # Library search paths
# set(CMAKE_EXE_LINKER_FLAGS_INIT "${CMAKE_EXE_LINKER_FLAGS_INIT} -L${PICOLIBC_SYSROOT}/lib")
# set(CMAKE_EXE_LINKER_FLAGS_INIT "${CMAKE_EXE_LINKER_FLAGS_INIT} -L${GCC_TOOLCHAIN}/lib/gcc/riscv64-unknown-elf/15.2.0")
# set(CMAKE_EXE_LINKER_FLAGS_INIT "${CMAKE_EXE_LINKER_FLAGS_INIT} -L${GCC_TOOLCHAIN}/riscv64-unknown-elf/lib")
#
# set(CMAKE_FIND_ROOT_PATH ${PICOLIBC_SYSROOT} ${GCC_TOOLCHAIN})
# set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
# set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
# set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

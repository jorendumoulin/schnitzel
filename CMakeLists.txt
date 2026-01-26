cmake_minimum_required(VERSION 3.12)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Specify the target system
# set(CMAKE_SYSTEM_NAME Generic)  # Bare-metal
# set(CMAKE_SYSTEM_PROCESSOR riscv64)
#
# set(CMAKE_C_COMPILER   /home/joren/Downloads/riscv/bin/riscv64-unknown-elf-gcc)
# set(CMAKE_CXX_COMPILER /home/joren/Downloads/riscv/bin/riscv64-unknown-elf-g++)

# Sysroot for headers and libraries
# set(PICOLIBC_SYSROOT /usr/local/picolibc/riscv64-unknown-elf)
# set(CMAKE_SYSROOT ${PICOLIBC_SYSROOT})

# Make the compiler find headers
# include_directories(SYSTEM ${PICOLIBC_SYSROOT}/include)

project(schnitzel)

# Global paths:
set(PROJECT_ROOT ${CMAKE_SOURCE_DIR})
set(TOOLCHAIN_ROOT ${PROJECT_ROOT}/cmake)
set(GENERATED_DIR ${PROJECT_ROOT}/generated)
set(VERILATED_DIR ${PROJECT_ROOT}/verilated)

# add_subdirectory(host)
add_subdirectory(sw)
add_subdirectory(tests/apps)
add_subdirectory(spitchel)

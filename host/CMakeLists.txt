cmake_minimum_required(VERSION 3.20)

if(NOT CMAKE_TOOLCHAIN_FILE)
  set(CMAKE_TOOLCHAIN_FILE
      "${CMAKE_CURRENT_SOURCE_DIR}/toolchain.cmake"
      CACHE FILEPATH "Toolchain file")
endif()

project(host C CXX ASM)

add_library(host STATIC
    crt0.S
    syscalls.c
    host.c
)
target_link_options(host INTERFACE
    # Supply a custom startup and linker script:
    -T ${CMAKE_CURRENT_SOURCE_DIR}/link.ld
    -nostartfiles
    # Disable warning about load with rwx permisisons
    -Wl,--no-warn-rwx-segments
    # Overwrite newlib's _write stub:
    -Wl,--wrap=_write
    -Wl,--undefined=__wrap__write
)


add_executable(hello_world hello_world.cpp)
target_link_libraries(hello_world PRIVATE host)


# Add these flags to your C and CXX flags
# add_compile_options(-ffunction-sections -fdata-sections)
# add_compile_options(-fno-exceptions -fno-rtti)

# target_link_options(executorch_test PRIVATE -Wl,--gc-sections)

# Configure and include executorch:
set(EXECUTORCH_BUILD_CPUINFO OFF CACHE BOOL "Disable cpuinfo (requires pthreads)" FORCE)
set(EXECUTORCH_BUILD_PTHREADPOOL OFF CACHE BOOL "Disable pthreadpool (requires pthreads)" FORCE)
set(EXECUTORCH_PAL_DEFAULT minimal CACHE STRING "")
set(EXECUTORCH_DTYPE_SELECTIVE_BUILD ON CACHE BOOL "")
set(EXECUTORCH_ENABLE_LOGGING OFF CACHE BOOL "")
set(EXECUTORCH_SELECT_ALL_OPS OFF CACHE BOOL "")
set(EXECUTORCH_BUILD_EXECUTOR_RUNNER OFF CACHE BOOL "")

# set(EXECUTORCH_USE_DL OFF CACHE BOOL "" FORCE)
# set(EXECUTORCH_ENABLE_DTYPE_SELECTIVE_BUILD ON CACHE BOOL "" FORCE)
# add_definitions(-Wno-error=unterminated-string-initialization)
add_subdirectory("../submodules/executorch/" "executorch")

add_executable(executorch_test main.cpp)

# Project-specific includes
target_include_directories(executorch_test PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../submodules
    ${CMAKE_CURRENT_SOURCE_DIR}/../submodules/executorch/third-party
    ${CMAKE_CURRENT_SOURCE_DIR}/../submodules/executorch/runtime/core/portable_type/c10
)

target_compile_definitions(executorch_test PRIVATE
    C10_USING_CUSTOM_GENERATED_MACROS
    EXECUTORCH_ENABLE_LOGGING=OFF
    EXECUTORCH_PAL_DEFAULT=minimal
)

target_compile_options(executorch_test PRIVATE -Os -ffunction-sections -fdata-sections)

target_link_libraries(
    executorch_test
    PRIVATE
        host
        executorch         # Core Runtime
        executorch_core
        portable_kernels    # Clean C++ math ops (no FFT/Eigen dependencies)
        -Wl,--whole-archive
        portable_ops_lib
        -Wl,--no-whole-archive
)

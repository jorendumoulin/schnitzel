# Compile and link the runtime library
enable_language(ASM)
add_library(runtime STATIC crt0.S)
target_sources(runtime PRIVATE sim/htif_runtime.c)
target_link_options(runtime PRIVATE
    -nostdlib
    -nostartfiles
    -fuse-ld=lld
    -T link.ld
    -L${CMAKE_CURRENT_SOURCE_DIR}
)

# Picolibc:
# Add Picolibc as a subdirectory
# set(CMAKE_TOOLCHAIN_FILE ${CMAKE_SOURCE_DIR}/cmake/riscv-toolchain.cmake)
# add_subdirectory(${CMAKE_SOURCE_DIR}/submodules/picolibc ${CMAKE_BINARY_DIR}/picolibc-build)
# target_link_libraries(runtime PRIVATE ${CMAKE_BINARY_DIR}/picolibc-build/libc.a)
# target_include_directories(runtime PRIVATE ${CMAKE_SOURCE_DIR}/submodules/picolibc/newlib/libc/include)
# target_include_directories(runtime PRIVATE ${CMAKE_BINARY_DIR}/picolibc-build/picolibc/include)
#
# # Printf:
# Configure printf library
target_compile_definitions(runtime PRIVATE
    PRINTF_ALIAS_STANDARD_FUNCTION_NAMES_SOFT
    #PRINTF_INTEGER_BUFFER_SIZE=16
    #PRINTF_DECIMAL_BUFFER_SIZE=16
    #PRINTF_DEFAULT_FLOAT_PRECISION=6
    #PRINTF_MAX_INTEGRAL_DIGITS_FOR_DECIMAL=9
    PRINTF_SUPPORT_DECIMAL_SPECIFIERS=NO
    PRINTF_SUPPORT_EXPONENTIAL_SPECIFIERS=NO
    SUPPORT_MSVC_STYLE_INTEGER_SPECIFIERS=NO
    PRINTF_SUPPORT_WRITEBACK_SPECIFIER=NO
    PRINTF_SUPPORT_LONG_LONG=NO
    PRINTF_USE_DOUBLE_INTERNALLY=NO
)
target_sources(runtime PRIVATE ${CMAKE_SOURCE_DIR}/submodules/printf/src/printf/printf.c)
target_include_directories(runtime PRIVATE ${CMAKE_SOURCE_DIR}/submodules/printf/src/printf)
target_include_directories(runtime PRIVATE ${CMAKE_SOURCE_DIR}/submodules/printf/src)
#
# target_link_libraries(runtime PRIVATE clang_rt.builtins-riscv)
#

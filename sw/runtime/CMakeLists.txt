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

# printf:
target_compile_definitions(runtime PRIVATE
    PRINTF_ALIAS_STANDARD_FUNCTION_NAMES_HARD
    PRINTF_SUPPORT_DECIMAL_SPECIFIERS=NO
    PRINTF_SUPPORT_EXPONENTIAL_SPECIFIERS=NO
    SUPPORT_MSVC_STYLE_INTEGER_SPECIFIERS=NO
    PRINTF_SUPPORT_WRITEBACK_SPECIFIER=NO
    PRINTF_SUPPORT_LONG_LONG=NO
    PRINTF_USE_DOUBLE_INTERNALLY=NO
)
target_sources(runtime PRIVATE ${CMAKE_SOURCE_DIR}/submodules/printf/src/printf/printf.c)
target_include_directories(runtime PRIVATE ${CMAKE_SOURCE_DIR}/submodules/printf/src)

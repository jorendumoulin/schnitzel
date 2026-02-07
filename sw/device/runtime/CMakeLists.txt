
add_library(device_runtime STATIC
  # start files
  crt0.S
  # putchar_ support via htif runtime:
  ${CMAKE_SOURCE_DIR}/sw/common/htif/htif_runtime.c
  # printf implementation
  ${CMAKE_SOURCE_DIR}/submodules/printf/src/printf/printf.c
)

# printf settings:
target_compile_definitions(device_runtime PRIVATE
    PRINTF_ALIAS_STANDARD_FUNCTION_NAMES_HARD
    PRINTF_SUPPORT_DECIMAL_SPECIFIERS=NO
    PRINTF_SUPPORT_EXPONENTIAL_SPECIFIERS=NO
    SUPPORT_MSVC_STYLE_INTEGER_SPECIFIERS=NO
    PRINTF_SUPPORT_WRITEBACK_SPECIFIER=NO
    PRINTF_SUPPORT_LONG_LONG=NO
    PRINTF_USE_DOUBLE_INTERNALLY=NO
)

target_include_directories(device_runtime PRIVATE
  ${CMAKE_SOURCE_DIR}/submodules/printf/src
)

target_link_options(device_runtime INTERFACE
    # Supply a custom startup and linker script:
    -T${CMAKE_CURRENT_SOURCE_DIR}/link.ld
    -nostartfiles
    -nostdlib
    -fuse-ld=lld
)


enable_language(ASM)
add_library(runtime STATIC
  # start files
  crt0.S
  # putchar_ support via htif runtime:
  ../../common/htif/htif_runtime.c
  # printf implementation
  ${CMAKE_SOURCE_DIR}/submodules/printf/src/printf/printf.c
)

# printf settings:
target_compile_definitions(runtime PRIVATE
    PRINTF_ALIAS_STANDARD_FUNCTION_NAMES_HARD
    PRINTF_SUPPORT_DECIMAL_SPECIFIERS=NO
    PRINTF_SUPPORT_EXPONENTIAL_SPECIFIERS=NO
    SUPPORT_MSVC_STYLE_INTEGER_SPECIFIERS=NO
    PRINTF_SUPPORT_WRITEBACK_SPECIFIER=NO
    PRINTF_SUPPORT_LONG_LONG=NO
    PRINTF_USE_DOUBLE_INTERNALLY=NO
)

target_include_directories(runtime PRIVATE
  ${CMAKE_SOURCE_DIR}/submodules/printf/src
)

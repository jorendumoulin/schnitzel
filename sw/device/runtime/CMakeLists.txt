include(CMakePackageConfigHelpers)

add_library(device_runtime STATIC
  # start files
  crt0.S
  # putchar_ support via htif runtime:
  ${ROOT}/sw/common/htif/htif_runtime.c
  # printf implementation
  ${ROOT}/submodules/printf/src/printf/printf.c
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
  ${ROOT}/submodules/printf/src
)

target_link_options(device_runtime INTERFACE
    # Supply a custom startup and linker script:
    -T${CMAKE_CURRENT_SOURCE_DIR}/link.ld
    -nostdlib
    -fuse-ld=lld
)

add_subdirectory(dma)

# Install the runtime to link with external cmake projects:

install(TARGETS device_runtime
        EXPORT RuntimeTargets
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
        RUNTIME DESTINATION bin
        INCLUDES DESTINATION include)

install(
    DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/
    DESTINATION include
)

install(
    DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../../common/mlir/
    DESTINATION include
)

install(EXPORT RuntimeTargets
        FILE RuntimeTargets.cmake
        NAMESPACE Runtime::
        DESTINATION lib/cmake/Runtime)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/RuntimeConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/RuntimeConfig.cmake
    INSTALL_DESTINATION lib/cmake/Runtime
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/RuntimeConfig.cmake
    DESTINATION lib/cmake/Runtime
)

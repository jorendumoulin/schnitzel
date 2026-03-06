# Configure executorch:
set(EXECUTORCH_BUILD_CPUINFO OFF CACHE BOOL "Disable cpuinfo (requires pthreads)" FORCE)
set(EXECUTORCH_BUILD_PTHREADPOOL OFF CACHE BOOL "Disable pthreadpool (requires pthreads)" FORCE)
set(EXECUTORCH_PAL_DEFAULT posix CACHE STRING "")
set(EXECUTORCH_DTYPE_SELECTIVE_BUILD OFF CACHE BOOL "")
set(EXECUTORCH_ENABLE_LOGGING ON CACHE BOOL "")
set(EXECUTORCH_INCLUDE_ALL_OPS ON CACHE BOOL "")
set(EXECUTORCH_LOG_LEVEL Debug CACHE STRING "" FORCE)
# set(EXECUTORCH_SELECT_OPS_LIST "aten::_to_copy.out,aten::add.out")
set(EXECUTORCH_BUILD_EXECUTOR_RUNNER OFF CACHE BOOL "")

# Use gcc for compiling executorch subprojects:
add_subdirectory("${ROOT}/submodules/executorch/" "executorch")

add_executable(hello_torch.elf
    hello_torch.cpp
)


if(NOT EXECUTORCH_ROOT)
  set(EXECUTORCH_ROOT ${ROOT}/submodules/executorch/)
endif()

include(${EXECUTORCH_ROOT}/tools/cmake/Utils.cmake)
include(${EXECUTORCH_ROOT}/tools/cmake/Codegen.cmake)
set(ENV{PYTHONPATH} "${EXECUTORCH_ROOT}")

set(_common_compile_options -Wno-deprecated-declarations -fPIC)

# Let files say "include <executorch/path/to/header.h>".
set(_common_include_directories ${EXECUTORCH_ROOT}/..)

executorch_load_build_variables()

gen_selected_ops(LIB_NAME "custom_ops_lib" ROOT_OPS "my_ops::mul3.out")

generate_bindings_for_kernels(
  LIB_NAME "custom_ops_lib" CUSTOM_OPS_YAML
  ${CMAKE_CURRENT_SOURCE_DIR}/kernels.yml
)
message("Generated files ${gen_command_sources}")

# generate_bindings_for_kernels(
#   LIB_NAME "custom_ops_lib" CUSTOM_OPS_YAML
#   ${CMAKE_CURRENT_LIST_DIR}/custom_ops.yaml
# )

# CMakeLists.txt (relevant fragment)
add_library(custom_kernels STATIC
    custom_kernel.cpp
)

target_link_libraries(custom_kernels
    executorch
)

gen_operators_lib(
  LIB_NAME "custom_ops_lib" KERNEL_LIBS custom_kernels DEPS executorch
)

# Project-specific includes
target_include_directories(hello_torch.elf PRIVATE
    ${ROOT}/sw/common/htif/
    ${ROOT}/submodules
    ${ROOT}/submodules/executorch/third-party
    ${ROOT}/submodules/executorch/runtime/core/portable_type/c10
)

target_compile_definitions(hello_torch.elf PRIVATE
    C10_USING_CUSTOM_GENERATED_MACROS
    EXECUTORCH_ENABLE_LOGGING=ON
    EXECUTORCH_PAL_DEFAULT=posix
)

target_compile_options(hello_torch.elf PRIVATE -Os -ffunction-sections -fdata-sections)

target_link_libraries(
    hello_torch.elf
    PRIVATE
        host_runtime
        executorch
        # executorch_selected_kernels
        custom_ops_lib
        portable_ops_lib
        portable_kernels
)

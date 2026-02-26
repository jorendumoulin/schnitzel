
# Configure executorch:
set(EXECUTORCH_BUILD_CPUINFO OFF CACHE BOOL "Disable cpuinfo (requires pthreads)" FORCE)
set(EXECUTORCH_BUILD_PTHREADPOOL OFF CACHE BOOL "Disable pthreadpool (requires pthreads)" FORCE)
set(EXECUTORCH_PAL_DEFAULT minimal CACHE STRING "")
set(EXECUTORCH_DTYPE_SELECTIVE_BUILD OFF CACHE BOOL "")
set(EXECUTORCH_ENABLE_LOGGING ON CACHE BOOL "")
set(EXECUTORCH_SELECT_ALL_OPS ON CACHE BOOL "")
set(EXECUTORCH_BUILD_EXECUTOR_RUNNER OFF CACHE BOOL "")


# Use gcc for compiling executorch subprojects:
add_subdirectory("${ROOT}/submodules/executorch/" "executorch")


# Project-specific includes
target_include_directories(executorch_test PRIVATE
    ${ROOT}/submodules
    ${ROOT}/submodules/executorch/third-party
    ${ROOT}/submodules/executorch/runtime/core/portable_type/c10
)

target_compile_definitions(executorch_test PRIVATE
    C10_USING_CUSTOM_GENERATED_MACROS
    EXECUTORCH_ENABLE_LOGGING=ON
    EXECUTORCH_PAL_DEFAULT=minimal
)

target_compile_options(executorch_test PRIVATE -Os -ffunction-sections -fdata-sections)

target_link_libraries(
    executorch_test
    PRIVATE
        host
        executorch
        portable_ops_lib
        portable_kernels    # Clean C++ math ops (no FFT/Eigen dependencies)
)

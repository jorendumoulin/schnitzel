cmake_minimum_required(VERSION 3.20)
project(gemm_app LANGUAGES CXX)

set(ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../..")

include(${ROOT}/cmake/mlir_source.cmake)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

message(STATUS "Install Directory: ${CMAKE_INSTALL_PREFIX}")

# --------------------------------------------------
# Parameters passed from command line
# --------------------------------------------------
set(GEMM_M 16 CACHE STRING "Matrix dimension M")
set(GEMM_K 16 CACHE STRING "Matrix dimension K")
set(GEMM_N 16 CACHE STRING "Matrix dimension N")

message(STATUS "GEMM sizes: M=${GEMM_M} K=${GEMM_K} N=${GEMM_N}")

# --------------------------------------------------
# Find the installed runtime package
# User passes:
#   -DCMAKE_PREFIX_PATH=/path/to/runtime/install
# --------------------------------------------------
find_package(Runtime REQUIRED)

# --------------------------------------------------
# Python needed to generate MLIR
# --------------------------------------------------
find_package(Python3 REQUIRED COMPONENTS Interpreter)

# --------------------------------------------------
# Generate gemm.mlir from gemm.py
# --------------------------------------------------
set(GENERATED_MLIR ${CMAKE_CURRENT_BINARY_DIR}/gemm.mlir)

add_custom_command(
    OUTPUT ${GENERATED_MLIR}
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/gemm.py
            --m ${M} --k ${K} --n ${N}
            -o ${GENERATED_MLIR}
    DEPENDS ${CMAKE_SOURCE_DIR}/gemm.py
    COMMENT "Generating gemm.mlir (M=${M},K=${K},N=${N})"
)

add_custom_target(generate_gemm_mlir DEPENDS ${GENERATED_MLIR})

# --------------------------------------------------
# Build executable
# --------------------------------------------------
add_executable(gemm gemm.cpp)
add_dependencies(gemm generate_gemm_mlir)

target_compile_definitions(gemm PRIVATE
    GEMM_M=${GEMM_M}
    GEMM_K=${GEMM_K}
    GEMM_N=${GEMM_N}
)

# --------------------------------------------------
# Link against installed runtimes
# These come from RuntimeTargets.cmake
# --------------------------------------------------
target_link_libraries(gemm PRIVATE
    Runtime::device_runtime
)

# --------------------------------------------------
# Your MLIR pipeline hook
# --------------------------------------------------
target_add_mlir_source(
    gemm
    ${GENERATED_MLIR}
    CONFIG "${ROOT}/generated/config.json"
)

# --------------------------------------------------
# Install this executable too (optional)
# --------------------------------------------------
install(TARGETS gemm RUNTIME DESTINATION bin)

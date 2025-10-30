cmake_minimum_required(VERSION 3.12)
project(spitchel CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find dependencies
find_package(verilator HINTS $ENV{VERILATOR_ROOT})
find_package(PkgConfig REQUIRED)
pkg_check_modules(FESVR REQUIRED riscv-fesvr)

# Paths
set(SCHNITZEL_ROOT ${CMAKE_SOURCE_DIR}/..)
set(GENERATED_DIR ${SCHNITZEL_ROOT}/generated)
set(VERILATED_DIR ${SCHNITZEL_ROOT}/verilated)

file(MAKE_DIRECTORY ${GENERATED_DIR})
file(MAKE_DIRECTORY ${VERILATED_DIR})

# Generate Verilog from Chisel
add_custom_command(
  OUTPUT ${GENERATED_DIR}/Core.sv
  COMMAND ${SCHNITZEL_ROOT}/mill schnitzel.runMain spitchel.EmitVerilog
  WORKING_DIRECTORY ${SCHNITZEL_ROOT}
  COMMENT "Generating Verilog from Chisel..."
)

# Verilate the core
add_custom_command(
  OUTPUT ${VERILATED_DIR}/VCore__ALL.a
  COMMAND verilator --cc --build -O3
    --top-module Core
    -Mdir ${VERILATED_DIR}
    --prefix VCore
    ${GENERATED_DIR}/*.sv
  DEPENDS ${GENERATED_DIR}/Core.sv
  WORKING_DIRECTORY ${SCHNITZEL_ROOT}
  COMMENT "Verilating Core..."
)

add_custom_target(verilate ALL DEPENDS ${VERILATED_DIR}/VCore__ALL.a)

# Spitchel executable
add_executable(spitchel
  src/main.cpp
  src/spitchel.cpp
  src/memory.cpp
)

add_dependencies(spitchel verilate)

target_include_directories(spitchel PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${FESVR_INCLUDE_DIRS}
  ${VERILATOR_ROOT}/include
  ${VERILATED_DIR}
)

target_link_libraries(spitchel PRIVATE
  ${VERILATED_DIR}/VCore__ALL.a
  ${FESVR_LIBRARIES}
)

target_sources(spitchel PRIVATE
  ${VERILATOR_ROOT}/include/verilated.cpp
)

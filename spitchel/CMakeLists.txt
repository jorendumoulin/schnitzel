set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find dependencies
find_package(verilator HINTS $ENV{VERILATOR_ROOT})
find_package(PkgConfig REQUIRED)
#pkg_check_modules(FESVR REQUIRED riscv-fesvr)

message(STATUS "PROJECT_ROOT in root subdir: ${GENERATED_DIR}")

#file(MAKE_DIRECTORY ${GENERATED_DIR})
#file(MAKE_DIRECTORY ${VERILATED_DIR})

set(CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS} -O3)

# Generate Verilog from Chisel
#add_custom_command(
#  OUTPUT ${GENERATED_DIR}/Core.sv
#  COMMAND ${PROJECT_ROOT}/mill schnitzel.runMain spitchel.EmitVerilog
#  WORKING_DIRECTORY ${PROJECT_ROOT}
#  COMMENT "Generating Verilog from Chisel..."
#)

# Verilate the core
# add_custom_command(
#   OUTPUT ${VERILATED_DIR}/VTop__ALL.a
#   COMMAND verilator --cc --build -O3
#     --top-module Core
#     -Mdir ${VERILATED_DIR}
#     --trace
#     --prefix VCore
#     ${GENERATED_DIR}/*.sv
#   DEPENDS ${GENERATED_DIR}/Core.sv
#   WORKING_DIRECTORY ${PROJECT_ROOT}
#   COMMENT "Verilating Core..."
# )

#add_custom_target(verilate ALL DEPENDS ${VERILATED_DIR}/VTop__ALL.a)

# RISC-V Bootrom
# Convert bootrom binary into C array to be embedded in simulator
add_custom_command(
    OUTPUT ${CMAKE_BINARY_DIR}/sw/bootrom/bootrom.c
    COMMAND xxd -i -n bootrom_data ${CMAKE_BINARY_DIR}/sw/bootrom/bootrom.bin > ${CMAKE_BINARY_DIR}/sw/bootrom/bootrom.c
    DEPENDS ${CMAKE_BINARY_DIR}/sw/bootrom/bootrom.bin
)
# Compile as library
add_library(bootrom_data STATIC ${CMAKE_BINARY_DIR}/sw/bootrom/bootrom.c)
add_dependencies(bootrom_data bootrom)

# Spitchel executable
add_executable(spitchel
  src/main.cpp
  src/sim.cpp
  src/memory.cpp
  src/loader.cpp
  src/dynamic_memory.cpp
  src/axi_interface.cpp
)

# add_dependencies(spitchel verilate)

target_include_directories(spitchel PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${FESVR_INCLUDE_DIRS}
  ${VERILATOR_ROOT}/include
  ${VERILATOR_ROOT}/include/vltstd
  ${VERILATED_DIR}
)

target_link_libraries(spitchel PRIVATE
  ${VERILATED_DIR}/VTop__ALL.a
  ${FESVR_LIBRARIES}
  bootrom_data
)

target_sources(spitchel PRIVATE
  ${VERILATOR_ROOT}/include/verilated.cpp
  ${VERILATOR_ROOT}/include/verilated_vcd_c.cpp
  ${VERILATOR_ROOT}/include/verilated_threads.cpp
)

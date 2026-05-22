cmake_minimum_required(VERSION 3.14)

include(${CMAKE_CURRENT_SOURCE_DIR}/../cmake/ccache.cmake)

project(sim CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)

set(SIM_OPT_FAST "-O3 -march=native" CACHE STRING
    "Optimization flags for Verilator OPT_FAST. Override to a portable -march for CI.")

find_package(elfio REQUIRED)
find_package(argparse REQUIRED)
find_package(verilator REQUIRED)

add_library(sim SHARED
  src/main.cpp
  src/sim.cpp
  src/dpi_memory.cpp
  src/dpi_host.cpp
  src/loader.cpp
  src/dynamic_memory.cpp
)

target_include_directories(sim PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(sim PRIVATE argparse::argparse elfio::elfio)

# All RTL sources, include dirs, and defines come from the root Bender
# manifest. No project-specific file enumeration lives here — adding new
# RTL or new submodules is done in Bender.yml, not in cmake.
#
# The path to the chisel-generated RTL directory is communicated to bender
# via the `SCHNITZEL_RTL_DIR` env var so that this build tree can be one of
# many parallel system builds (each pairing a generated/ dir with a build/
# dir). Override with `-DSCHNITZEL_RTL_DIR=...` when configuring cmake.
set(SCHNITZEL_RTL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../generated" CACHE PATH
    "Directory containing the chisel-generated RTL and its auto-emitted Bender.yml.")

# Have bender render a small cmake snippet (BENDER_SOURCES / BENDER_DEFINES /
# BENDER_INCDIRS) via its Tera template engine. include()-ing that snippet
# avoids any hand-rolled string parsing in cmake.
set(BENDER_CMAKE ${CMAKE_CURRENT_BINARY_DIR}/bender.cmake)
execute_process(
    COMMAND ${CMAKE_COMMAND} -E env "SCHNITZEL_RTL_DIR=${SCHNITZEL_RTL_DIR}"
            bender script template
                -t simulation -t ibex_tracing -D RVFI
                --template=${CMAKE_CURRENT_SOURCE_DIR}/bender.cmake.tera
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/..
    OUTPUT_FILE ${BENDER_CMAKE}
    COMMAND_ERROR_IS_FATAL ANY
)
include(${BENDER_CMAKE})

verilate(sim
    SOURCES ${BENDER_SOURCES}
    TOP_MODULE TopWrapper
    PREFIX VTopWrapper
    TRACE
    THREADS ${CMAKE_HOST_SYSTEM_PROCESSOR_COUNT}
    OPT_FAST "${SIM_OPT_FAST}"
    OPT_SLOW "-O0"
    VERILATOR_ARGS
        -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-LATCH
        -Wno-BLKANDNBLK -Wno-SELRANGE -Wno-SYMRSVDWORD
        -Wno-CMPCONST -Wno-UNSIGNED -Wno-WIDTH -Wno-ASCRANGE
        -Wno-IMPLICITSTATIC
        ${BENDER_DEFINES}
        ${BENDER_INCDIRS}
        --assert
)


# C simulator
add_executable(csim src/main.cpp)
target_link_libraries(csim PRIVATE sim argparse::argparse)
target_include_directories(csim PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
set_target_properties(csim  PROPERTIES OUTPUT_NAME sim)

# Python lib
find_package(pybind11 REQUIRED)
pybind11_add_module(my_module src/python_bindings.cpp)
target_link_libraries(my_module PRIVATE sim)
target_include_directories(my_module PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

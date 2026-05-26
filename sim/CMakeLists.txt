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
#
# `-t synthesis -t verilator` mirrors what `bender script verilator` auto-
# activates internally. Without these, `not(synthesis)`-gated files (e.g.
# tech_cells_generic's deprecated pad_functional.sv, which uses 1995-style
# pmos primitives Verilator can't handle) get pulled in.
set(BENDER_CMAKE ${CMAKE_CURRENT_BINARY_DIR}/bender.cmake)

# Bender pins the resolved value of `$SCHNITZEL_RTL_DIR` into Bender.lock at
# update time and reads it from there on subsequent `bender script` calls,
# ignoring the current env var. Multiple kernel builds in this repo each
# need their own generated/ dir, so refresh the lock here against this
# build's SCHNITZEL_RTL_DIR before rendering the filelist. Local parallel
# kernel builds in the same checkout race on Bender.lock — CI runs one
# kernel per checkout so it's unaffected.
execute_process(
    COMMAND ${CMAKE_COMMAND} -E env "SCHNITZEL_RTL_DIR=${SCHNITZEL_RTL_DIR}"
            bender update
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/..
    COMMAND_ERROR_IS_FATAL ANY
)

execute_process(
    COMMAND ${CMAKE_COMMAND} -E env "SCHNITZEL_RTL_DIR=${SCHNITZEL_RTL_DIR}"
            bender script template
                -t synthesis -t verilator
                -t sim_top -t ibex_tracing -t cv64a6_imafdc_sv39 -D RVFI
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
        # Bender follows cva6's manifest faithfully and pulls in every
        # file of every transitive dep (axi, common_cells, ...) even when
        # our design hierarchy never instantiates them. That introduces
        # benign noise the old hand-curated flatten flow avoided:
        #   PINMISSING  — uninstantiated axi/cva6 modules have pins our
        #                 wrappers don't drive.
        #   REDEFMACRO  — ibex and common_cells both define `ASSERT/`ASSUME
        #                 macros with slightly different signatures.
        # And `--bbox-unsup` stubs out language constructs Verilator does
        # not implement (notably `default disable iff` outside `ifndef
        # VERILATOR` in axi_id_remap.sv).
        -Wno-PINMISSING -Wno-REDEFMACRO
        --bbox-unsup
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

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

# RTL sources come from the root Bender.yml, which pulls in three path
# dependencies — src/main/resources/{cva6,ibex}/Bender.yml and the chisel-
# emitted manifest at $SCHNITZEL_RTL_DIR. Each sub-manifest references its
# submodule via an env var ($CVA6_PATH, $IBEX_PATH, $SCHNITZEL_RTL_DIR).
# Bender substitutes them at script time but treats the substituted value
# as relative to the sub-manifest dir, so the defaults below are written
# relative to src/main/resources/{cva6,ibex}/ — i.e. four levels up to the
# repo root, then back down into submodules/.
set(SCHNITZEL_RTL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../generated" CACHE PATH
    "Directory containing the chisel-generated RTL and its auto-emitted Bender.yml.")
set(CVA6_PATH "../../../../submodules/cva6" CACHE STRING
    "Path to the cva6 submodule, resolved relative to src/main/resources/cva6/Bender.yml.")
set(IBEX_PATH "../../../../submodules/ibex" CACHE STRING
    "Path to the ibex submodule, resolved relative to src/main/resources/ibex/Bender.yml.")

set(BENDER_ENV
    "SCHNITZEL_RTL_DIR=${SCHNITZEL_RTL_DIR}"
    "CVA6_PATH=${CVA6_PATH}"
    "IBEX_PATH=${IBEX_PATH}")

set(BENDER_CMAKE ${CMAKE_CURRENT_BINARY_DIR}/bender.cmake)

# Bender pins the resolved value of `$SCHNITZEL_RTL_DIR` into Bender.lock at
# update time, so refresh the lock against this build's value before
# rendering the filelist. Parallel kernel builds in one checkout race on
# Bender.lock — CI runs one kernel per checkout so it's unaffected.
execute_process(
    COMMAND ${CMAKE_COMMAND} -E env ${BENDER_ENV} bender update
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/..
    COMMAND_ERROR_IS_FATAL ANY
)

execute_process(
    COMMAND ${CMAKE_COMMAND} -E env ${BENDER_ENV}
            bender script template
                -t sim_top
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

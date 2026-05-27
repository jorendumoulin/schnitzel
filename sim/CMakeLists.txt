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

# RTL sources come from the root Bender.yml
set(SCHNITZEL_RTL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../generated")
set(CVA6_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../submodules/cva6")
set(IBEX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../submodules/ibex")

cmake_path(ABSOLUTE_PATH SCHNITZEL_RTL_DIR NORMALIZE)
cmake_path(ABSOLUTE_PATH CVA6_PATH NORMALIZE)
cmake_path(ABSOLUTE_PATH IBEX_PATH NORMALIZE)

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
                -t simulation
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
        -Wno-IMPLICITSTATIC -Wno-PINMISSING
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

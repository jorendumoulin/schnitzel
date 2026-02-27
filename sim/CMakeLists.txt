cmake_minimum_required(VERSION 3.14)
project(sim CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(verilator REQUIRED)

add_executable(sim
    src/main.cpp
    src/sim.cpp
    src/memory.cpp
    src/loader.cpp
    src/dynamic_memory.cpp
)
target_include_directories(sim PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

verilate(sim
    SOURCES
        ${CMAKE_CURRENT_SOURCE_DIR}/../generated/Top.sv
    TOP_MODULE Top
    PREFIX VTop
    TRACE_VCD
    THREADS ${CMAKE_HOST_SYSTEM_PROCESSOR_COUNT}
    VERILATOR_ARGS
        "-Wno-UNOPTFLAT" "-Wno-MULTIDRIVEN" "-Wno-LATCH"
        "-Wno-BLKANDNBLK" "-Wno-SELRANGE" "-Wno-SYMRSVDWORD"
        "-Wno-CMPCONST" "-Wno-UNSIGNED" "-Wno-WIDTH" "-Wno-ASCRANGE"
        "-Wno-IMPLICITSTATIC" "-I${CMAKE_CURRENT_SOURCE_DIR}/../generated/"
)

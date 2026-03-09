cmake_minimum_required(VERSION 3.14)
project(sim CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(elfio REQUIRED)
find_package(argparse REQUIRED)
find_package(verilator REQUIRED)

add_executable(sim
    src/main.cpp
    src/sim.cpp
    src/dpi_memory.cpp
    src/dpi_host.cpp
    src/loader.cpp
    src/dynamic_memory.cpp
)
target_include_directories(sim PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(sim PRIVATE argparse::argparse elfio::elfio)

set(GENERATED_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../generated)
set(RTL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/rtl)

file(READ ${GENERATED_DIR}/filelist.f FILELIST_CONTENT)
string(REPLACE "\n" ";" FILELIST ${FILELIST_CONTENT})

set(RTL_SOURCES
    ${RTL_DIR}/TopWrapper.sv
    ${RTL_DIR}/MemDpi.sv
)

foreach(f ${FILELIST})
  string(STRIP "${f}" f_stripped)
  if(NOT f_stripped STREQUAL "")
    list(APPEND RTL_SOURCES ${GENERATED_DIR}/${f_stripped})
  endif()
endforeach()

verilate(sim
    SOURCES ${RTL_SOURCES}
    TOP_MODULE TopWrapper
    PREFIX VTopWrapper
    TRACE_VCD
    THREADS ${CMAKE_HOST_SYSTEM_PROCESSOR_COUNT}
    OPT_FAST "-O3 -march=native"
    OPT_SLOW "-O0"
    VERILATOR_ARGS
        -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-LATCH
        -Wno-BLKANDNBLK -Wno-SELRANGE -Wno-SYMRSVDWORD
        -Wno-CMPCONST -Wno-UNSIGNED -Wno-WIDTH -Wno-ASCRANGE
        -Wno-IMPLICITSTATIC
        -I${GENERATED_DIR}/
        -I${RTL_DIR}/
)

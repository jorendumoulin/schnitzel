project(sim)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(verilator REQUIRED)

add_executable(sim
    src/main.cpp
    src/sim.cpp
    src/memory.cpp
    src/loader.cpp
    src/dynamic_memory.cpp
)
target_include_directories(sim PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_options(sim PRIVATE -O3)

verilate(sim
    SOURCES
        ${CMAKE_SOURCE_DIR}/generated/Top.sv
    TOP_MODULE Top
    PREFIX VTop
    TRACE
    THREADS ${CMAKE_HOST_SYSTEM_PROCESSOR_COUNT}
    VERILATOR_ARGS
        "-Wno-UNOPTFLAT" "-Wno-MULTIDRIVEN" "-Wno-LATCH"
        "-Wno-BLKANDNBLK" "-Wno-SELRANGE" "-Wno-SYMRSVDWORD"
        "-Wno-CMPCONST" "-Wno-UNSIGNED" "-Wno-WIDTH" "-Wno-ASCRANGE"
        "-I${CMAKE_SOURCE_DIR}/generated/"
)




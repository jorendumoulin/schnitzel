cmake_minimum_required(VERSION 3.14)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../")

if(NOT CMAKE_TOOLCHAIN_FILE)
  set(CMAKE_TOOLCHAIN_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/runtime/ibex-toolchain.cmake"
    CACHE FILEPATH "Ibex Toolchain file")
endif()

project(device ASM C CXX)

include(${CMAKE_SOURCE_DIR}/../cmake/mlir_source.cmake)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../common/mlir)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/runtime)
set(RUNTIME_PATH "${CMAKE_CURRENT_SOURCE_DIR}/runtime")

add_subdirectory(runtime)
add_subdirectory(apps)

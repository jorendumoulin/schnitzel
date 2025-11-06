cmake_minimum_required(VERSION 3.12)
project(schnitzel)

# Global paths:
set(PROJECT_ROOT ${CMAKE_SOURCE_DIR})
set(TOOLCHAIN_ROOT ${PROJECT_ROOT}/cmake)
set(GENERATED_DIR ${PROJECT_ROOT}/generated)
set(VERILATED_DIR ${PROJECT_ROOT}/verilated)

add_subdirectory(sw)
add_subdirectory(spitchel)

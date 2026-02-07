if(NOT CMAKE_TOOLCHAIN_FILE)
  set(CMAKE_TOOLCHAIN_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/runtime/ibex-toolchain.cmake"
    CACHE FILEPATH "Ibex Toolchain file")
endif()


project(device ASM C)

# TODO: why do i need to include the toolchain?
# does cmake not do this for me?
# do i have to do everything myself?
include("${CMAKE_TOOLCHAIN_FILE}")


set(RUNTIME_PATH "${CMAKE_CURRENT_SOURCE_DIR}/runtime")

add_subdirectory(runtime)
add_subdirectory(apps)

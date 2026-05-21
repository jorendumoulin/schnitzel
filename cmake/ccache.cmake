# Enable ccache as a compiler launcher when available, for C/CXX/ASM.
# Include from a top-level CMakeLists.txt before project() so the launchers
# are picked up for every language and propagated to subdirectories.

find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM)
  message(STATUS "ccache found: ${CCACHE_PROGRAM} -- enabling compiler launcher")
  set(CMAKE_C_COMPILER_LAUNCHER   "${CCACHE_PROGRAM}")
  set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
  set(CMAKE_ASM_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
endif()

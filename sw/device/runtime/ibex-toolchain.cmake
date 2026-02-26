set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR riscv32)

# Do not check compiler, it only works with custom sw runtime
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

set(CMAKE_ASM_COMPILER /usr/bin/clang)
set(CMAKE_C_COMPILER /usr/bin/clang)
set(CMAKE_CXX_COMPILER /usr/bin/clang++)

set(DEFAULT_COMPILE_FLAGS
  "-O2 --target=riscv32-unkown-elf -march=rv32imc -mabi=ilp32"
)

set(CMAKE_ASM_FLAGS ${DEFAULT_COMPILE_FLAGS})
set(CMAKE_C_FLAGS ${DEFAULT_COMPILE_FLAGS})
set(CMAKE_CXX_FLAGS ${DEFAULT_COMPILE_FLAGS})
set(CMAKE_EXE_LINKER_FLAGS "${DEFAULT_COMPILE_FLAGS} -fuse-ld=lld" CACHE STRING "" FORCE)



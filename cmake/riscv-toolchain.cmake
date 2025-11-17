set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR riscv32)

set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)
set(CMAKE_ASM_COMPILER clang)
set(CMAKE_OBJCOPY llvm-objcopy)

set(CMAKE_ASM_FLAGS "-O2 --target=riscv32-unknown-elf -march=rv32imc -mabi=ilp32")
set(CMAKE_C_FLAGS "-O2 --target=riscv32-unknown-elf -march=rv32imc -mabi=ilp32")
set(CMAKE_CXX_FLAGS "-O2 --target=riscv32-unknown-elf -march=rv32imc -mabi=ilp32")

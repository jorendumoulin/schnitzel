set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR riscv64)

set(CMAKE_C_COMPILER /home/joren/phd/spike-test/riscv-tools/bin/riscv64-unknown-elf-gcc)
set(CMAKE_CXX_COMPILER /home/joren/phd/spike-test/riscv-tools/bin/riscv64-unknown-elf-g++)
set(CMAKE_ASM_COMPILER /home/joren/phd/spike-test/riscv-tools/bin/riscv64-unknown-elf-gcc)
set(CMAKE_OBJCOPY /home/joren/phd/spike-test/riscv-tools/bin/riscv64-unknown-elf-objcopy)

set(CMAKE_C_FLAGS "-O2 -march=rv64imac -mabi=lp64")
set(CMAKE_CXX_FLAGS "-O2 -march=rv64imac -mabi=lp64")

flatten-ibex:
    make -C ./src/main/resources/ibex

flatten-cva6:
    make -C ./src/main/resources/cva6

generate-verilog top='default': flatten-ibex flatten-cva6
    ./mill schnitzel.runMain sim.EmitVerilog --top={{top}}

configure-quick:
    cmake -B build/sim -S sim -G Ninja -DSIM_OPT_FAST="-O0"

configure:
    cmake -B build/sim -S sim -G Ninja; \
    cmake -B build/host -S sw/host -G Ninja
    cmake -B build/device -S sw/device -G Ninja -DCMAKE_INSTALL_PREFIX=$PWD/install

build:
    cmake --build build/sim
    cmake --build build/host
    cmake --build build/device

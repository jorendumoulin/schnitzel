flatten-ibex:
    make -C ./src/main/resources/ibex

flatten-cva6:
    make -C ./src/main/resources/cva6

generate-verilog: flatten-ibex flatten-cva6
    ./mill schnitzel.runMain sim.EmitVerilog

generate-cluster: flatten-ibex
    ./mill schnitzel.runMain sim.ClusterOnlyEmitVerilog

configure:
    cmake -B build/sim -S sim -G Ninja
    cmake -B build/host -S sw/host -G Ninja
    cmake -B build/device -S sw/device -G Ninja

build:
    cmake --build build/sim
    cmake --build build/host
    cmake --build build/device

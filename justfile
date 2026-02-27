flatten-ibex:
    make -C ./src/main/resources/ibex

flatten-cva6:
    make -C ./src/main/resources/cva6

generate-verilog: flatten-ibex flatten-cva6
    ./mill schnitzel.runMain sim.EmitVerilog

configure fast='':
    ./mill schnitzel.runMain sim.EmitVerilog
    @if [ -n "{{fast}}" ]; then \
        cmake -B build/sim -S sim -G Ninja -DCMAKE_CXX_FLAGS=-O3; \
    else \
        cmake -B build/sim -S sim -G Ninja; \
    fi
    cmake -B build/host -S sw/host -G Ninja
    cmake -B build/device -S sw/device -G Ninja

build:
    cmake --build build/sim
    cmake --build build/host
    cmake --build build/device

flatten-ibex:
    make -C ./src/main/resources/ibex

generate-verilog: flatten-ibex
    ./mill schnitzel.runMain spitchel.EmitVerilog

verilate: generate-verilog
    verilator --cc --build -O3 -j $(nproc) \
        --top-module Core \
        -Mdir ./verilated \
        --trace \
        --prefix VCore \
        -Wno-UNOPTFLAT \
        -Wno-MULTIDRIVEN \
        ./generated/*.sv

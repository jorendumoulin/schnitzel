flatten-ibex:
    make -C ./src/main/resources/ibex

generate-verilog: flatten-ibex
    ./mill schnitzel.runMain spitchel.EmitVerilog

verilate: generate-verilog
    verilator --cc --build -j $(nproc) \
        --top-module Top \
        -Mdir ./verilated \
        --trace \
        --prefix VTop \
        -Wno-UNOPTFLAT \
        -Wno-MULTIDRIVEN \
        ./generated/*.sv

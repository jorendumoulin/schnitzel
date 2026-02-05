flatten-ibex:
    make -C ./src/main/resources/ibex

flatten-cva6:
    make -C ./src/main/resources/cva6

generate-verilog: flatten-ibex flatten-cva6
    ./mill schnitzel.runMain sim.EmitVerilog

verilate: generate-verilog
    OBJCACHE=ccache \
    verilator --cc --build -j $(nproc) \
        --top-module Top \
        -Mdir ./verilated \
        --trace \
        --prefix VTop \
        -Wno-UNOPTFLAT \
        -Wno-MULTIDRIVEN \
        -Wno-LATCH \
        -Wno-BLKANDNBLK \
        -Wno-SELRANGE \
        -Wno-SYMRSVDWORD \
        -Wno-CMPCONST \
        -Wno-UNSIGNED \
        -Wno-WIDTH \
        -Wno-ASCRANGE \
        -CFLAGS "-O3" \
        ./generated/*.sv


make-sim: verilate
    make -C ./build/ -j

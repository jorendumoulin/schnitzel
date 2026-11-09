default:
  @just --list

flatten-design top-module output:
    verilator -sv -E --top-module {{top-module}} generated/*.sv > {{output}}
    sed -i '/^`/s/^/\/\//' {{output}}

# Generate Verilog RTL for a given Top module configuration.
generate-verilog top='default' output='generated':
    ./mill schnitzel.runMain sim.EmitVerilog --top={{top}} --output-dir={{output}}

# Generate FPGA RTL and a Bender Vivado import script.
generate-fpga-vivado rtl='generated-fpga' script='/tmp/schnitzel-vivado.tcl':
    ./mill schnitzel.runMain sim.EmitVerilog --top=fpga --output-dir="{{rtl}}"
    SCHNITZEL_RTL_DIR="$PWD/{{rtl}}" CVA6_PATH="$PWD/submodules/cva6" IBEX_PATH="$PWD/submodules/ibex" .pixi/envs/default/bin/bender update
    SCHNITZEL_RTL_DIR="$PWD/{{rtl}}" CVA6_PATH="$PWD/submodules/cva6" IBEX_PATH="$PWD/submodules/ibex" .pixi/envs/default/bin/bender script vivado -t fpga -D SYNTHESIS -D FPGA_XILINX --no-simset > "{{script}}"
    echo 'add_files -norecurse $ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_assert_dummy_macros.svh' >> "{{script}}"
    echo 'add_files -norecurse $ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_assert_sec_cm.svh' >> "{{script}}"
    echo 'add_files -norecurse $ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_assert_yosys_macros.svh' >> "{{script}}"
    echo 'add_files -norecurse $ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_assert_standard_macros.svh' >> "{{script}}"
    echo 'add_files -norecurse $ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_macros.svh' >> "{{script}}"
    echo 'add_files -norecurse $ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_util_get_scramble_params.svh' >> "{{script}}"
    echo 'add_files -norecurse $ROOT/submodules/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_util_memload.svh' >> "{{script}}"
    echo 'add_files -norecurse $ROOT/submodules/ibex/vendor/lowrisc_ip/dv/sv/dv_utils/dv_fcov_macros.svh' >> "{{script}}"

configure-quick:
    cmake -B build/sim -S sim -G Ninja -DSIM_OPT_FAST="-O0"
    cmake -B build/host -S sw/host -G Ninja
    cmake -B build/device -S sw/device -G Ninja -DCMAKE_INSTALL_PREFIX=$PWD/install

configure:
    cmake -B build/sim -S sim -G Ninja; \
    cmake -B build/host -S sw/host -G Ninja
    cmake -B build/device -S sw/device -G Ninja -DCMAKE_INSTALL_PREFIX=$PWD/install

build:
    cmake --build build/sim
    cmake --build build/host
    cmake --build build/device

# Rewrite one submodule's origin from HTTPS to SSH (local only; .gitmodules untouched).
submodule-ssh submodule:
    #!/usr/bin/env bash
    set -euo pipefail
    cd submodules/{{submodule}}
    current=$(git remote get-url origin)
    new=$(echo "$current" | sed -E 's|https://github\.com/([^/]+)/(.+)|git@github.com:\1/\2|')
    git remote set-url origin "$new"
    echo "submodules/{{submodule}}: $current -> $new"

# Package the minimal Scala AXI4-Lite client as a Vivado IP.
package-simple-axi out='build/SimpleAxiClient-ip':
    bash -lc 'source /home/joren/vivado/settings64.sh && vivado -mode batch -source fpga/package_simple_axi.tcl -tclargs "{{out}}"'

# Build the minimal KV260 AXI path through bitstream generation.
build-simple-axi ip='build/SimpleAxiClient-ip' project='build/simple-axi':
    bash -lc 'source /home/joren/vivado/settings64.sh && vivado -mode batch -source fpga/build_simple_axi.tcl -tclargs "{{ip}}" "{{project}}"'

default:
  @just --list

flatten-cva6:
    make -C ./src/main/resources/cva6

flatten-design top-module output:
    verilator -sv -E --top-module {{top-module}} generated/*.sv > {{output}}
    sed -i '/^`/s/^/\/\//' {{output}}

# Generate Verilog RTL for a given Top module configuration.
generate-verilog top='default' output='generated': flatten-cva6
    ./mill schnitzel.runMain sim.EmitVerilog --top={{top}} --output-dir={{output}}

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

# FPGA integration

The Scala/Chisel sources are `src/main/scala/top/FPGATop.scala` and
`FPGAControl.scala`, with AXI-Lite types in `src/main/scala/axi/AXILite.scala`.
FPGATop instantiates Cluster directly for an external ARM host. Instantiate the
generated RTL in a Vivado block design alongside the Zynq processing system.

## Connections

- Drive `aclk` from a PS PL clock and `aresetn` from its reset controller.
  Reset assertion must cover a clock edge; deassert synchronously.
- Connect PS `M_AXI_HPM0_FPD` through protocol/width conversion to the 32-bit
  AXI-Lite `s_axi` interface. Assign a 4 KiB aperture: addresses are local offsets.
- Connect the 512-bit AXI4 `m_axi` through width conversion to PS `S_AXI_HP*_FPD`
  for DDR access. Preserve the six-bit IDs or use proper ID remapping.
- Both interfaces use `aclk`; any clock-domain conversion belongs outside this
  wrapper. There is no interrupt output; software polls status.

## Registers

All registers are 32-bit and aligned. Implemented write fields honor WSTRB[0].
Unmapped/unaligned accesses and writes to read-only registers return SLVERR.
The AXI-Lite bank accepts AW and W independently and holds stalled responses.

| Offset | Access | Meaning |
| --- | --- | --- |
| 0x00 | RW | Bit 0: RUN. Initially 0, holding Cluster in reset. Write 1 to start. Writing 0 clears the release token and barrier count. |
| 0x04 | RO | Bit 0: RUN; bit 1: both cores waiting at the global barrier; bit 2: release pending. |
| 0x08 | RW | Write bit 0 = 1 to queue one release token; read bit 0 = pending. Release while RUN=0 returns SLVERR. |
| 0x0c | RO | Completed barrier handshakes since cluster reset, modulo 2^32. |
| 0x10 | RW1C | Bit 0: sticky AXI response error (SLVERR/DECERR). Write 1 to clear. A new error wins over a simultaneous clear. |

A release is consumed only when the combined CSR request is valid at local
address zero (core CSR 0x800). Tokens may be queued before arrival. Repeated
writes while pending coalesce; a write on the consumption cycle queues another
token. Firmware determines whether a barrier means launch, completion, etc.

Only clear RUN when external transactions are quiescent: this wrapper does not
drain AXI traffic. Recovery during active traffic requires resetting Cluster and
the associated interconnect together. Control registers remain accessible with
RUN=0. The error flag survives RUN changes and clears on aresetn or software clear.

## Boot and limitations

Load firmware before setting RUN. Ibex boot base remains 0x10000, with the first
instruction at 0x10080. This wrapper provides no boot ROM or address translation.
Reserve/map memory accordingly, or add translation and update the software map.
Core data addresses at/above 0x10000000 currently route to TCDM, so DDR relocation
also needs to consider that split. Shared buffers need physical/DMA addresses
and cache management for the non-coherent HP path, not ordinary ARM virtual pointers.

The two previously discussed AXI adapter issues are unchanged. This is a starting
point, not validated board hardware. FPGATop connects the complete Chisel AXI
bundle and preserves the external interface during optimization. WLAST comes
from Cluster directly. Response errors are recorded here but not delivered to
the cores. Generated ports use Chisel bundle names (for example,
`m_axi_aw_bits_addr`, `s_axi_aw_bits_addr`, and `s_axi_b_bits`); map these to
the corresponding Vivado AXI interface signals when packaging the IP.

The default L3 metadata describes the 256 MiB logical aperture below the core's
TCDM split, not the board's physical DDR capacity. FPGATop accepts a MemoryConfig
constructor parameter for metadata; it does not implement address translation.

### Package the FPGA IP

The packaging script regenerates the Chisel RTL, resolves the Bender Vivado source list, and creates a packaged IP with `S_AXI_CTRL` (AXI4-Lite) and `M_AXI_MEM` (512-bit AXI4) interfaces:

```sh
source /home/joren/vivado/settings64.sh
vivado -mode batch -source fpga/package_ip.tcl -tclargs "$PWD/build/FPGATop-ip"
```

The packaged component is written to `build/FPGATop-ip/FPGATop/component.xml`. It declares a 32-bit, 256 MiB master address space so `M_AXI_MEM` appears in Address Editor. Add that directory as a Vivado IP repository.


## Build and verification

For Vivado, first generate the FPGA RTL:

```sh
just generate-verilog fpga generated-fpga
```

Then run Bender from the repository root:

```tcl
SCHNITZEL_RTL_DIR="$PWD/generated-fpga" \\
  .pixi/envs/default/bin/bender script vivado -t fpga -D SYNTHESIS --no-simset \\
  > /tmp/schnitzel-vivado.tcl
```

Source `/tmp/schnitzel-vivado.tcl` in Vivado. It adds the resolved source files,
include directories, and synthesis defines. The paths refer to the repository
and generated RTL directory; no copy or packaging utility is used. The
project-pinned Bender is preferred. Define `SYNTHESIS` and select `FPGATop` as
the synthesis top. CVA6 is a source dependency but is not instantiated.
Vivado resource utilization, RAM inference, and timing remain to be checked.

The Scala simulation test exercises FPGAControl directly: independent AW/W
arrival, response backpressure, byte strobes, reset, barriers, and errors.
It does not execute firmware or validate the cluster's AXI adapters:

```sh
./mill schnitzel.test.testOnly top.FPGAControlSpec
```

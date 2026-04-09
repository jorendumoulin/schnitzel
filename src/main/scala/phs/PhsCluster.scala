package phs

import chisel3._

import icache.InstructionCache
import core.{Core, DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig, AXIMux, DecoupledIOToAXI}
import interconnect.Interconnect
import chisel3.util.{SRAM, log2Up}
import memory.MemDemux
import csr.HWBarrier
import dma.Dma
import csr.{CsrDemux, CsrCombiner, CsrIO}

/** Self-contained PHS cluster with 2 RISC-V cores, shared TCDM, DMA, and PHS accelerators.
  *
  * Core 0 always has DMA (on the CsrDemux catch-all at 0x900). Core 1 has PHS accelerators (catch-all at 0x900).
  *
  * @param phsConfigs
  *   Per-core list of PHS accelerator configs. phsConfigs(0) = core 0 (expected empty), phsConfigs(1) = core 1.
  */
class PhsCluster(phsConfigs: Seq[Seq[PhsAcceleratorConfig]]) extends Module {

  require(phsConfigs.length == 2, "PhsCluster requires exactly 2 cores of configs")
  require(phsConfigs(0).isEmpty, "Core 0 PHS accelerators not yet supported (DMA occupies the catch-all)")
  require(phsConfigs(1).length == 1, "Currently supports exactly 1 PHS accelerator on core 1")

  val wideAxiDataWidth = 512
  val tcdmDataWidth = CoreConfig.dataWidth

  val io = IO(new Bundle {
    val axi = new AXIBundle(AXIConfig(idWidth = 6, dataWidth = wideAxiDataWidth))
    val csr = new CsrIO()
  })

  // ---- Cores ----
  val core_0 = Module(new Core(2))
  val core_1 = Module(new Core(1))

  // ---- Memory demuxes (split data interface into AXI <> TCDM) ----
  val memMux_0 = Module(new MemDemux(CoreConfig.addrWidth, CoreConfig.dataWidth, 0x10000000))
  memMux_0.io.in <> core_0.io.dmem
  val memMux_1 = Module(new MemDemux(CoreConfig.addrWidth, CoreConfig.dataWidth, 0x10000000))
  memMux_1.io.in <> core_1.io.dmem

  // ---- AXI interfaces for cores ----
  val mem_to_axi_0 = Module(
    new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, AXIConfig(dataWidth = wideAxiDataWidth), 1)
  )
  memMux_0.io.outs(0) <> mem_to_axi_0.io.bus
  val mem_to_axi_1 = Module(
    new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, AXIConfig(dataWidth = wideAxiDataWidth), 2)
  )
  memMux_1.io.outs(0) <> mem_to_axi_1.io.bus

  // ---- DMA on core 0 (catch-all at 0x900) ----
  val dma = Module(
    new Dma(addrWidth = CoreConfig.addrWidth, dataWidth = tcdmDataWidth, AXIConfig(dataWidth = wideAxiDataWidth), 3)
  )

  // ---- CSR Demux core 0: barrier(0x800) + local barrier(0x810) + DMA catch-all ----
  val csrDemux_0 = Module(new CsrDemux(3, Seq((0x800L, 0x10L), (0x810L, 0x10L))))
  csrDemux_0.io.in <> core_0.io.csr
  dma.io.csr <> csrDemux_0.io.outs(2)

  // ---- PHS Accelerator on core 1 (catch-all at 0x900) ----
  val phsAccel = Module(
    new PhsAccelerator(CoreConfig.addrWidth, tcdmDataWidth, phsConfigs(1).head, csrBase = 0x900)
  )

  // ---- CSR Demux core 1: barrier(0x800) + local barrier(0x810) + accel catch-all ----
  val csrDemux_1 = Module(new CsrDemux(3, Seq((0x800L, 0x10L), (0x810L, 0x10L))))
  csrDemux_1.io.in <> core_1.io.csr
  phsAccel.io.csr <> csrDemux_1.io.outs(2)

  // ---- Global synchronization CSR (0x800) ----
  val csrCombiner = Module(new CsrCombiner(2))
  csrCombiner.io.ins(0) <> csrDemux_0.io.outs(0)
  csrCombiner.io.ins(1) <> csrDemux_1.io.outs(0)
  csrCombiner.io.out <> io.csr

  // ---- Cluster hw barrier (local synchronization 0x810) ----
  val barrier = Module(new HWBarrier(2))
  barrier.io.ins <> Seq(csrDemux_0.io.outs(1), csrDemux_1.io.outs(1))

  // ---- Instruction Cache ----
  val icache = Module(new InstructionCache(2))
  icache.io.imems <> VecInit(Seq(core_0.io.imem, core_1.io.imem))

  // ---- TCDM ----
  val accPorts = phsAccel.io.tcdmPorts.toSeq
  val numInterconnectPorts = 2 + dma.io.data.length + accPorts.length
  val numBanks = 32
  val tcdm_sram = VecInit(Seq.fill(numBanks)(SRAM.masked(1024, Vec(4, UInt(8.W)), 0, 0, 1)))
  val tcdm_ports = VecInit(tcdm_sram.map(sram => sram.readwritePorts(0)))

  val interconnect = Module(new Interconnect(numInterconnectPorts, numBanks, CoreConfig.addrWidth, tcdmDataWidth))

  interconnect.io.ins <> VecInit(
    Seq(memMux_0.io.outs(1), memMux_1.io.outs(1))
  ) ++ dma.io.data ++ accPorts

  interconnect.io.outs.zip(tcdm_ports).foreach { case (out, port) =>
    port.enable := out.req.valid
    port.address := out.req.bits.addr(CoreConfig.addrWidth - 1, log2Up(numBanks) + log2Up(CoreConfig.dataWidth / 8))
    port.isWrite := out.req.bits.wen
    port.mask.foreach { _ := out.req.bits.ben.asBools }
    port.writeData := out.req.bits.wdata.asTypeOf(Vec(4, UInt(8.W)))
    out.rsp.bits.data := port.readData.asUInt
    out.req.ready := true.B
    val prevReq = RegNext(out.req.fire)
    out.rsp.valid := prevReq
  }

  // ---- AXI Crossbar ----
  val axiMux = Module(AXIMux(AXIConfig(dataWidth = wideAxiDataWidth, idWidth = 4), 4))
  axiMux.io.ins <> VecInit(icache.io.axi, mem_to_axi_0.io.axi, mem_to_axi_1.io.axi, dma.io.axi)
  axiMux.io.out <> io.axi

  // ---- Config export ----
  def getConfig: PhsClusterConfig = PhsClusterConfig(
    PhsMemoryConfig("L1", 0x1000_0000L, 0x1_0000L),
    List(
      PhsCoreConfig(1, phsConfigs(1).map(cfg =>
        PhsAccelPhsEntry("phs", cfg.streamers, cfg.numSwitches, cfg.switchBitwidths, cfg.moduleName, cfg.svPath)
      ).toList),
      PhsCoreConfig(2, List(PhsAccelDmaEntry("dma")))
    )
  )
}

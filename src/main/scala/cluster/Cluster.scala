package cluster

import chisel3._

import icache.InstructionCache
import core.{Core, DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig, AXIMux, DecoupledIOToAXI}
import interconnect.Interconnect
import chisel3.util.{SRAM, Cat, log2Ceil, log2Up}
import memory.MemDemux
import csr.HWBarrier
import dma.Dma
import csr.{CsrDemux, CsrCombiner, CsrOp, CsrReq}
import chisel3.util.Decoupled
import accelerator.PhsAccelerator
import csr.CsrIO
import config.{ClusterConfig, MemoryConfig, PhsAcceleratorConfig}

/** Cluster with 2 RISC-V cores, shared TCDM, DMA, and configurable PHS accelerators.
  *
  * @param phsConfigs
  *   Per-core list of PHS accelerator configs. phsConfigs(0) = core 0, phsConfigs(1) = core 1. Core 0 always has
  *   DMA. Default matches the original ALU accelerator on core 1.
  */
class Cluster(
    phsConfigs: Seq[Seq[PhsAcceleratorConfig]] = Seq(Seq(), Seq(PhsAcceleratorConfig.defaultAlu))
) extends Module {

  require(phsConfigs.length == 2, "Cluster has exactly 2 cores")

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

  // ---- DMA on core 0 ----
  val dma = Module(
    new Dma(addrWidth = CoreConfig.addrWidth, dataWidth = tcdmDataWidth, AXIConfig(dataWidth = wideAxiDataWidth), 3)
  )

  // ---- PHS Accelerators ----
  val phsAccelModules = phsConfigs.map { coreConfigs =>
    coreConfigs.map(cfg => Module(new PhsAccelerator(CoreConfig.addrWidth, tcdmDataWidth, cfg)))
  }

  // ---- CSR Demux for core 0 ----
  // Address map: barrier(0x800) + local barrier(0x810) + PHS accels(0x920+) + DMA(catch-all)
  // PHS accels start at 0x920 to avoid DMA's CSR range at 0x900-0x917
  val core0PhsRanges = phsConfigs(0).indices.map(i => (0x920L + i * 0x20L, 0x20L))
  val core0NumOuts = 2 + phsConfigs(0).length + 1
  val core0AddrMap = Seq((0x800L, 0x10L), (0x810L, 0x10L)) ++ core0PhsRanges
  val csrDemux_0 = Module(new CsrDemux(core0NumOuts, core0AddrMap))
  csrDemux_0.io.in <> core_0.io.csr
  dma.io.csr <> csrDemux_0.io.outs(core0NumOuts - 1) // DMA on catch-all
  phsAccelModules(0).zipWithIndex.foreach { case (acc, i) =>
    acc.io.csr <> csrDemux_0.io.outs(2 + i)
  }

  // ---- CSR Demux for core 1 ----
  // Address map: barrier(0x800) + local barrier(0x810) + PHS accels(0x900+) + catch-all(tied off)
  val core1PhsRanges = phsConfigs(1).indices.map(i => (0x900L + i * 0x20L, 0x20L))
  val core1NumOuts = 2 + phsConfigs(1).length + 1
  val core1AddrMap = Seq((0x800L, 0x10L), (0x810L, 0x10L)) ++ core1PhsRanges
  val csrDemux_1 = Module(new CsrDemux(core1NumOuts, core1AddrMap))
  csrDemux_1.io.in <> core_1.io.csr
  phsAccelModules(1).zipWithIndex.foreach { case (acc, i) =>
    acc.io.csr <> csrDemux_1.io.outs(2 + i)
  }
  // Tie off catch-all on core 1 (no DMA)
  csrDemux_1.io.outs(core1NumOuts - 1).req.ready := true.B
  csrDemux_1.io.outs(core1NumOuts - 1).rsp.rdata := 0.U

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
  val phsTotalPorts = phsConfigs.flatten.map(_.totalTcdmPorts).sum
  val numInterconnectPorts = 2 + 16 + phsTotalPorts // 2 cores + DMA(16) + PHS accels
  val numBanks = 32
  val tcdm_sram = VecInit(Seq.fill(numBanks)(SRAM.masked(1024, Vec(4, UInt(8.W)), 0, 0, 1)))
  val tcdm_ports = VecInit(tcdm_sram.map(sram => sram.readwritePorts(0)))

  val interconnect = Module(new Interconnect(numInterconnectPorts, numBanks, CoreConfig.addrWidth, tcdmDataWidth))

  val allTcdmPorts = VecInit(Seq(memMux_0.io.outs(1), memMux_1.io.outs(1))) ++
    dma.io.data ++
    phsAccelModules.flatten.flatMap(_.io.tcdmPorts)

  interconnect.io.ins <> allTcdmPorts

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
  def getConfig: ClusterConfig = ClusterConfig(
    MemoryConfig("L1", 0x1_0000_0000L, 0x1_0000L),
    List(
      config.CoreConfig(1, phsAccelModules(1).map(_.getConfig).toList),
      config.CoreConfig(2, List(dma.getConfig) ++ phsAccelModules(0).map(_.getConfig).toList)
    )
  )
}

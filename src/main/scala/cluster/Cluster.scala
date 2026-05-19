package cluster

import chisel3._

import icache.InstructionCache
import core.CoreConfig
import axi.{AXIBundle, AXIConfig, AXIMux}
import interconnect.Interconnect
import csr.{CsrCombiner, CsrIO, HWBarrier}
import dma.Dma
import accelerator.AluAccelerator
import memory.BankedMemory
import config.{ClusterConfig, MemoryConfig}

class Cluster extends Module {

  val wideAxiDataWidth = 512
  val tcdmDataWidth = CoreConfig.dataWidth

  val io = IO(new Bundle {
    val axi = new AXIBundle(AXIConfig(idWidth = 6, dataWidth = wideAxiDataWidth))
    val csr = new CsrIO()
  })

  val wideAxiCfg = AXIConfig(dataWidth = wideAxiDataWidth)

  // Accelerators -- created up front so each core's CSR demux can attach to them.
  val dma = Dma(addrWidth = CoreConfig.addrWidth, dataWidth = tcdmDataWidth, axiConfig = wideAxiCfg)
  val aluAccelerator = AluAccelerator(addrWidth = CoreConfig.addrWidth, dataWidth = tcdmDataWidth)

  // Per-core subsystems (Core + mem split + width converter + AXI adapter + CSR demux).
  val core_0 = CoreSubsystem(
    hartId = 2,
    accelerator = dma.io.csr,
    tcdmDataWidth = tcdmDataWidth,
    wideAxiCfg = wideAxiCfg
  )
  val core_1 = CoreSubsystem(
    hartId = 1,
    accelerator = aluAccelerator.io.csr,
    tcdmDataWidth = tcdmDataWidth,
    wideAxiCfg = wideAxiCfg
  )

  // Global synchronization CSR (0x800) - coupled and sent externally
  CsrCombiner(inputs = Seq(core_0.globalCsr, core_1.globalCsr), output = io.csr)

  // Cluster hw barrier (local synchronization 0x810)
  HWBarrier(inputs = Seq(core_0.localCsr, core_1.localCsr))

  // Instruction Cache
  val icache = InstructionCache(Seq(core_0.imem, core_1.imem))

  // TCDM
  val accPorts = aluAccelerator.io.aData ++ aluAccelerator.io.bData ++ aluAccelerator.io.cData
  val tcdm_ports = BankedMemory(numBanks = 32, depth = 1024, dataWidth = tcdmDataWidth)

  Interconnect(
    inputs = Seq(core_0.tcdm, core_1.tcdm) ++ dma.io.data ++ accPorts,
    outputs = tcdm_ports
  )

  // AXI Crossbar
  AXIMux(
    inputs = Seq(icache.io.axi, core_0.axi, core_1.axi, dma.io.axi),
    output = io.axi
  )

  def getConfig: ClusterConfig = ClusterConfig(
    MemoryConfig("L1", 0x1000_0000L, 0x1_0000L),
    List(
      config.CoreConfig(1, List(aluAccelerator.getConfig)),
      config.CoreConfig(2, List(dma.getConfig))
    )
  )

}

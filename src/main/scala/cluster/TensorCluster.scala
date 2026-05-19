package cluster

import chisel3._

import icache.InstructionCache
import core.{Core, DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig, AXIMux, DecoupledIOToAXI}
import interconnect.Interconnect
import chisel3.util.SRAM
import memory.MemDemux
import csr.HWBarrier
import dma.Dma
import csr.{CsrDemux, CsrCombiner, CsrOp, CsrReq}
import chisel3.util.Decoupled
import icache.InstructionCache
import accelerator.TensorCore
import csr.CsrIO
import config.ClusterConfig
import config.MemoryConfig
import memory.MemWidthConverter

class TensorCluster extends Module {

  val wideAxiDataWidth = 512
  val tcdmDataWidth = 64

  val io = IO(new Bundle {
    val axi = new AXIBundle(AXIConfig(idWidth = 6, dataWidth = wideAxiDataWidth))
    val csr = new CsrIO()
  })

  // Define the first RISC-V Core:
  // RISC-V Core
  val core_0 = Module(new Core(2))

  // Split data interface into AXI <> TCDM
  val memMux_0 = Module(new MemDemux(CoreConfig.addrWidth, CoreConfig.dataWidth, 0x10000000));
  memMux_0.io.in <> core_0.io.dmem
  val memWidthConverter_0 = Module(new MemWidthConverter(CoreConfig.addrWidth, 32, tcdmDataWidth))
  memWidthConverter_0.io.in <> memMux_0.io.outs(1)

  // Convert data interface to AXI
  val mem_to_axi_0 = Module(
    new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, AXIConfig(dataWidth = wideAxiDataWidth), 1)
  )
  memMux_0.io.outs(0) <> mem_to_axi_0.io.bus

  val csrDemux_0 = Module(new CsrDemux(3, Seq((0x800L, 0x10L), (0x810L, 0x10L))))
  csrDemux_0.io.in <> core_0.io.csr

  // Attach dma to first core:
  val dma = Module(
    new Dma(addrWidth = CoreConfig.addrWidth, dataWidth = tcdmDataWidth, AXIConfig(dataWidth = wideAxiDataWidth), 3)
  )
  dma.io.csr <> csrDemux_0.io.outs(2)

  // Second core:
  val core_1 = Module(new Core(1))

  // Split data interface into AXI <> TCDM
  val memMux_1 = Module(new MemDemux(CoreConfig.addrWidth, CoreConfig.dataWidth, 0x10000000));
  memMux_1.io.in <> core_1.io.dmem
  val memWidthConverter_1 = Module(new MemWidthConverter(CoreConfig.addrWidth, 32, tcdmDataWidth))
  memWidthConverter_1.io.in <> memMux_1.io.outs(1)

  // Convert data interface to AXI
  val mem_to_axi_1 = Module(
    new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, AXIConfig(dataWidth = wideAxiDataWidth), 2)
  )
  memMux_1.io.outs(0) <> mem_to_axi_1.io.bus

  val csrDemux_1 = Module(new CsrDemux(3, Seq((0x800L, 0x10L), (0x810L, 0x10L))))
  csrDemux_1.io.in <> core_1.io.csr

  // Attach accelerator to second core:
  val tensorCore = Module(
    new TensorCore(addrWidth = CoreConfig.addrWidth, dataWidth = tcdmDataWidth, M = 8, N = 8, K = 8)
  )
  tensorCore.io.csr <> csrDemux_1.io.outs(2)

  // Global synchronization CSR (0x800) - coupled and sent externally
  val csrCombiner = Module(new CsrCombiner(2))
  csrCombiner.io.ins(0) <> csrDemux_0.io.outs(0)
  csrCombiner.io.ins(1) <> csrDemux_1.io.outs(0)
  csrCombiner.io.out <> io.csr

  // Cluster hw barrier (local synchronization 0x810)
  val barrier = Module(new HWBarrier(2));
  barrier.io.ins <> Seq(csrDemux_0.io.outs(1), csrDemux_1.io.outs(1))

  // Instruction Cache
  val icache = Module(new InstructionCache(2))
  icache.io.imems <> VecInit(Seq(core_0.io.imem, core_1.io.imem));

  // Accelerator ports:
  val accPorts = tensorCore.io.aData ++ tensorCore.io.bData ++ tensorCore.io.cData

  // TCDM
  val numBanks = 64
  val tcdm_sram = VecInit(Seq.fill(numBanks)(SRAM.masked(1024, Vec(tcdmDataWidth / 8, UInt(8.W)), 0, 0, 1)));
  val tcdm_ports = VecInit(tcdm_sram.map(sram => sram.readwritePorts(0)));

  Interconnect(
    inputs = Seq(memWidthConverter_0.io.out, memWidthConverter_1.io.out) ++ dma.io.data ++ accPorts,
    outputs = tcdm_ports
  )

  // AXI Crossbar
  val axiMux = Module(AXIMux(AXIConfig(dataWidth = wideAxiDataWidth, idWidth = 4), 4))
  axiMux.io.ins <> VecInit(icache.io.axi, mem_to_axi_0.io.axi, mem_to_axi_1.io.axi, dma.io.axi)
  axiMux.io.out <> io.axi

  def getConfig: ClusterConfig = ClusterConfig(
    MemoryConfig("L1", 0x1000_0000L, 0x1_0000L),
    List(
      config.CoreConfig(1, List(tensorCore.getConfig)),
      config.CoreConfig(2, List(dma.getConfig))
    )
  )

}

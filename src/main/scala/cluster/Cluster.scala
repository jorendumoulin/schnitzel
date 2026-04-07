package cluster

import chisel3._

import icache.InstructionCache
import core.{Core, DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig, AXIMux, DecoupledIOToAXI}
import interconnect.Interconnect
import chisel3.util.{SRAM, log2Up}
import memory.MemDemux
import csr.HWBarrier
import dma.Dma
import csr.{CsrDemux, CsrCombiner}
import accelerator.AluAccelerator
import csr.CsrIO
import config.{ClusterConfig, MemoryConfig}

/** Handle to an instantiated accelerator's ports for Cluster wiring.
  *
  * @param tcdmPorts
  *   TCDM memory ports to connect to the interconnect
  * @param csrPort
  *   CSR interface port
  * @param csrRange
  *   CSR address range (base, size) for CsrDemux routing
  * @param accelConfig
  *   Accelerator config for metadata export
  */
class AcceleratorHandle(
    val tcdmPorts: Seq[DecoupledBusIO],
    val csrPort: CsrIO,
    val csrRange: (Long, Long),
    val accelConfig: _root_.config.Accelerator
)

/** Cluster with 2 RISC-V cores, shared TCDM, DMA, and configurable accelerators.
  *
  * Override [[makeAccelerators]] in subclasses to provide custom accelerators. The default creates an AluAccelerator on
  * core 1, matching the original hardcoded behavior.
  */
class Cluster extends Module {

  val wideAxiDataWidth = 512
  val tcdmDataWidth = CoreConfig.dataWidth

  val io = IO(new Bundle {
    val axi = new AXIBundle(AXIConfig(idWidth = 6, dataWidth = wideAxiDataWidth))
    val csr = new CsrIO()
  })

  /** Override in subclasses to provide custom accelerators per core. Returns Seq[Seq[AcceleratorHandle]] indexed by
    * core (must be length 2). Default: AluAccelerator on core 1.
    */
  protected def makeAccelerators(): Seq[Seq[AcceleratorHandle]] = {
    val alu = Module(new AluAccelerator(CoreConfig.addrWidth, tcdmDataWidth))
    Seq(
      Seq(), // core 0: no accelerators
      Seq(
        new AcceleratorHandle(
          tcdmPorts = (alu.io.aData ++ alu.io.bData ++ alu.io.cData).toSeq,
          csrPort = alu.io.csr,
          csrRange = (0x900L, 0x20L),
          accelConfig = alu.getConfig
        )
      )
    )
  }

  val accelerators = makeAccelerators()
  require(accelerators.length == 2, "Cluster has exactly 2 cores")

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
  val dmaHandle = new AcceleratorHandle(
    tcdmPorts = dma.io.data.toSeq,
    csrPort = dma.io.csr,
    csrRange = (0x900L, 0x20L),
    accelConfig = dma.getConfig
  )

  // ---- CSR Demux ----
  // Each core gets: barrier(0x800) + local barrier(0x810) + device CSR ranges.
  // Core 0 devices: DMA + accelerators. Core 1 devices: accelerators only.
  val core0Devices = Seq(dmaHandle) ++ accelerators(0)
  val core1Devices = accelerators(1)

  val csrDemux_0 = Module(
    new CsrDemux(
      Seq((0x800L, 0x10L), (0x810L, 0x10L)) ++ core0Devices.map(_.csrRange)
    )
  )
  csrDemux_0.io.in <> core_0.io.csr
  core0Devices.zipWithIndex.foreach { case (dev, i) =>
    dev.csrPort <> csrDemux_0.io.outs(2 + i)
  }

  val csrDemux_1 = Module(
    new CsrDemux(
      Seq((0x800L, 0x10L), (0x810L, 0x10L)) ++ core1Devices.map(_.csrRange)
    )
  )
  csrDemux_1.io.in <> core_1.io.csr
  core1Devices.zipWithIndex.foreach { case (dev, i) =>
    dev.csrPort <> csrDemux_1.io.outs(2 + i)
  }

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
  val allDeviceTcdmPorts = (core0Devices ++ core1Devices).flatMap(_.tcdmPorts)
  val numInterconnectPorts = 2 + allDeviceTcdmPorts.length // 2 cores + all devices
  val numBanks = 32
  val tcdm_sram = VecInit(Seq.fill(numBanks)(SRAM.masked(1024, Vec(4, UInt(8.W)), 0, 0, 1)))
  val tcdm_ports = VecInit(tcdm_sram.map(sram => sram.readwritePorts(0)))

  val interconnect = Module(new Interconnect(numInterconnectPorts, numBanks, CoreConfig.addrWidth, tcdmDataWidth))

  interconnect.io.ins <> VecInit(Seq(memMux_0.io.outs(1), memMux_1.io.outs(1))) ++ allDeviceTcdmPorts

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
      config.CoreConfig(1, core1Devices.map(_.accelConfig).toList),
      config.CoreConfig(2, core0Devices.map(_.accelConfig).toList)
    )
  )
}

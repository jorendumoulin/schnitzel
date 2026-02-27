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
import csr.CsrDemux
import icache.InstructionCache
import accelerator.AluAccelerator

class Cluster extends Module {

  val io = IO(new Bundle {
    val axi = new AXIBundle(AXIConfig(idWidth = 6, dataWidth = 512))
  })

  // Define the first RISC-V Core:
  // RISC-V Core
  val core_0 = Module(new Core(2))

  // Split data interface into AXI <> TCDM
  val memMux_0 = Module(new MemDemux(CoreConfig.addrWidth, CoreConfig.dataWidth, 0x10000000));
  memMux_0.io.in <> core_0.io.dmem

  // Convert data interface to AXI
  val mem_to_axi_0 = Module(
    new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, AXIConfig(dataWidth = 512), 1)
  )
  memMux_0.io.outs(0) <> mem_to_axi_0.io.bus

  val csrDemux_0 = Module(new CsrDemux(0x900))
  csrDemux_0.io.in <> core_0.io.csr

  // Attach dma to fist core:
  val dma = Module(new Dma(addrWidth = 32, dataWidth = 64, AXIConfig(dataWidth = 512), 3))
  dma.io.csr <> csrDemux_0.io.outs(1)

  // Second core:
  val core_1 = Module(new Core(1))

  // Split data interface into AXI <> TCDM
  val memMux_1 = Module(new MemDemux(CoreConfig.addrWidth, CoreConfig.dataWidth, 0x10000000));
  memMux_1.io.in <> core_1.io.dmem

  // Convert data interface to AXI
  val mem_to_axi_1 = Module(
    new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, AXIConfig(dataWidth = 512), 2)
  )
  memMux_1.io.outs(0) <> mem_to_axi_1.io.bus

  val csrDemux_1 = Module(new CsrDemux(0x900))
  csrDemux_1.io.in <> core_1.io.csr

  // Attach accelerator to second core:
  val aluAccelerator = Module(new AluAccelerator(addrWidth = 32, dataWidth = 64))
  aluAccelerator.io.csr <> csrDemux_1.io.outs(1)

  // Cluster hw barrier
  val barrier = Module(new HWBarrier(2));
  barrier.io.ins <> Seq(csrDemux_0.io.outs(0), csrDemux_1.io.outs(0))

  // Instruction Cache
  val icache = Module(new InstructionCache(2))
  icache.io.imems <> VecInit(Seq(core_0.io.imem, core_1.io.imem));

  // Acce
  val accPorts = aluAccelerator.io.aData ++ aluAccelerator.io.bData ++ aluAccelerator.io.cData

  // TCDM
  val numBanks = 32
  val tcdm_sram = VecInit(Seq.fill(numBanks)(SRAM.masked(1024, Vec(4, UInt(8.W)), 0, 0, 1)));
  val tcdm_ports = VecInit(tcdm_sram.map(sram => sram.readwritePorts(0)));

  val interconnect = Module(new Interconnect(22, numBanks, CoreConfig.addrWidth, CoreConfig.dataWidth));

  interconnect.io.ins <> VecInit(Seq(memMux_0.io.outs(1), memMux_1.io.outs(1))) ++ dma.io.data ++ accPorts

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

  // AXI Crossbar
  val axiMux = Module(new AXIMux(AXIConfig(dataWidth = 512, idWidth = 4), AXIConfig(dataWidth = 512, idWidth = 6), 4))
  axiMux.io.ins <> VecInit(icache.io.axi, mem_to_axi_0.io.axi, mem_to_axi_1.io.axi, dma.io.axi)
  axiMux.io.out <> io.axi

}

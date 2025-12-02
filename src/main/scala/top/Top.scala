package top

import chisel3._

import core.Core
import icache.ICache
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig, AXIMux}
import axi.DecoupledIOToAXI
import interconnect.Interconnect
import chisel3.util.SRAM
import chisel3.util.Cat
import chisel3.util.log2Ceil
import chisel3.util.log2Up
import memory.MemDemux

class Top extends Module {

  val io = IO(new Bundle {
    val axi = new AXIBundle(AXIConfig(dataWidth = 512))
  })

  // RISC-V Core
  val core = Module(new Core())

  // Split data interface into AXI <> TCDM
  val memMux = Module(new MemDemux(CoreConfig.addrWidth, CoreConfig.dataWidth, 0x10000000));
  memMux.io.in <> core.io.dmem

  // Convert data interface to AXI
  val mem_to_axi = Module(
    new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, AXIConfig(dataWidth = 512), 1)
  )
  memMux.io.outs(0) <> mem_to_axi.io.bus

  // Instruction Cache
  val icache = Module(new ICache())
  icache.io.imems <> VecInit(Seq(core.io.imem));

  // TCDM
  val numBanks = 32
  val tcdm_sram = VecInit(Seq.fill(numBanks)(SRAM(1024, UInt(32.W), 0, 0, 1)));
  val tcdm_ports = VecInit(tcdm_sram.map(sram => sram.readwritePorts(0)));
  val interconnect = Module(new Interconnect(1, numBanks, CoreConfig.addrWidth, CoreConfig.dataWidth));
  interconnect.io.ins <> VecInit(Seq(memMux.io.outs(1)))
  interconnect.io.outs.zip(tcdm_ports).foreach { case (out, port) =>
    port.enable := out.req.valid
    port.address := out.req.bits.addr(CoreConfig.addrWidth - 1, log2Up(numBanks) + log2Up(CoreConfig.dataWidth / 8))
    port.isWrite := out.req.bits.wen
    port.writeData := out.req.bits.wdata
    out.rsp.bits.data := port.readData
    out.req.ready := true.B
    val prevReq = RegNext(out.req.fire)
    out.rsp.valid := prevReq
  }

  // AXI Crossbar
  val axiMux = Module(new AXIMux(AXIConfig(dataWidth = 512), 2))
  axiMux.io.ins <> VecInit(icache.io.axi, mem_to_axi.io.axi)
  axiMux.io.out <> io.axi

}

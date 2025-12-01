package top

import chisel3._

import core.Core
import icache.ICache
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig, AXIMux}
import axi.DecoupledIOToAXI

class Top extends Module {

  val io = IO(new Bundle {
    val axi = new AXIBundle(AXIConfig(dataWidth = 512))
  })

  // RISC-V Core
  val core = Module(new Core())

  // Convert data interface to AXI
  val mem_to_axi = Module(
    new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, AXIConfig(dataWidth = 512), 1)
  )
  core.io.dmem <> mem_to_axi.io.bus

  // Instruction Cache
  val icache = Module(new ICache())
  icache.io.imems <> VecInit(Seq(core.io.imem));

  // AXI Crossbar
  val axiMux = Module(new AXIMux(AXIConfig(dataWidth = 512), 2))
  axiMux.io.ins <> VecInit(icache.io.axi, mem_to_axi.io.axi)
  axiMux.io.out <> io.axi

}

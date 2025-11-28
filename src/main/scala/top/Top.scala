package top

import chisel3._

import core.Core
import icache.ICache
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig}
import axi.DecoupledIOToAXI

class Top extends Module {

  val io = IO(new Bundle {

    val axi_wide = new AXIBundle(AXIConfig(dataWidth = 512))
    val axi_wide_2 = new AXIBundle(AXIConfig(dataWidth = 512))

  })

  val core = Module(new Core())

  val mem_to_axi = Module(
    new DecoupledIOToAXI(CoreConfig.addrWidth, CoreConfig.dataWidth, AXIConfig(dataWidth = 512), 1)
  )
  core.io.dmem <> mem_to_axi.io.bus
  mem_to_axi.io.axi <> io.axi_wide_2

  val icache = Module(new ICache())
  icache.io.imems <> VecInit(Seq(core.io.imem));

  io.axi_wide <> icache.io.axi

}

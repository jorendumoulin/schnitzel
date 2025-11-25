package top

import chisel3._

import core.Core
import icache.ICache
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig}

class Top extends Module {

  val io = IO(new Bundle {

    val axi_wide = new AXIBundle(AXIConfig(dataWidth = 512))

    val dmem =
      new DecoupledBusIO(
        CoreConfig.addrWidth,
        CoreConfig.dataWidth
      ) // Decoupled data memory interface
  })

  val core = Module(new Core())
  core.io.dmem <> io.dmem;

  val icache = Module(new ICache())
  icache.io.imems <> VecInit(Seq(core.io.imem));

  io.axi_wide <> icache.io.axi

}

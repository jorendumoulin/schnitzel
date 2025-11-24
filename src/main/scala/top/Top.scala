package top

import chisel3._

import core.Core
import icache.ICache
import core.{DecoupledBusIO, CoreConfig}

class Top extends Module {

  val io = IO(new Bundle {

    val imem =
      new DecoupledBusIO(
        32,
        512
      ) // Instruction memory interface

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

  io.imem <> icache.io.axi

}

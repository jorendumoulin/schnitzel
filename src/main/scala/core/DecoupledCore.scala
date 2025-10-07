package core

import chisel3._
import chisel3.util._
import chisel3.util.Decoupled

/** Decoupled Core: Connecting the core to a decoupled data interface */
class DeocupledCore extends Module {

  val io = IO(new Bundle {
    val imem =
      new BusIO(
        CoreConfig.addrWidth,
        CoreConfig.instrWidth
      ) // Instruction memory interface
    val dmem =
      new DecoupledBusIO(
        CoreConfig.addrWidth,
        CoreConfig.dataWidth
      ) // Decoupled data memory interface
  })

  val core = Module(new Core)

  // Standard imem interfance is simply connected through.
  io.imem <> core.io.imem

  // Load-store unit to handle the decoupled data interface.
  val lsu = Module(new LSU(CoreConfig.addrWidth, CoreConfig.dataWidth))
  lsu.io.in <> core.io.dmem
  io.dmem <> lsu.io.out

}

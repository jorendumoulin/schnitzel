package cluster

import chisel3._
import chisel3.util._
import core._

class Cluster extends Module {

  val io = IO(new Bundle {

    val imem =
      new DecoupledBusIO(
        CoreConfig.addrWidth,
        CoreConfig.instrWidth
      ) // Instruction memory interface

    val dmem =
      new DecoupledBusIO(
        CoreConfig.addrWidth,
        CoreConfig.dataWidth
      ) // Decoupled data memory interface
  })

}

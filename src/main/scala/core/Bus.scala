package core

import chisel3._
import chisel3.util._

/** Generic Bus interface for memory access using DecoupledIO. This can be
  * extended or replaced with a specific protocol as needed.
  */
class BusReq extends Bundle {
  val addr = UInt(64.W)
  val wdata = UInt(64.W)
  val wen = Bool()
  val ren = Bool()
}

class BusIO extends Bundle {
  val req = Decoupled(new BusReq) // .valid, .ready, .bits
  val rdata = Input(UInt(64.W))
}

/** Example stub for a Bus-connected memory using DecoupledIO. Replace or extend
  * with actual memory or peripheral logic.
  */
class BusMemoryStub extends Module {
  val io = IO(new BusIO)

  // Simple stub: always ready, returns zero data
  io.req.ready := true.B
  io.rdata := 0.U
}

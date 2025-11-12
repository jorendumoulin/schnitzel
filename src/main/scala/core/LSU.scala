package core

import chisel3._
import chisel3.util._

/** Bufferless implementation of a LSU. This makes the assumption that a request
  * will stay alive and stall all other things until the response has arrived.
  */
class LSU(addrWidth: Int, dataWidth: Int) extends Module {
  val io = IO(new Bundle {
    val in = Flipped(new BusIO(addrWidth, dataWidth)) // Data memory interface
    val out = new DecoupledBusIO(addrWidth, dataWidth)
  })

  // Propagate the requests to the decoupled bus
  io.out.req <> io.in.req

  // On a read request, only assert the valid signal when the response has arrived.
  when(!io.in.req.bits.wen) {
    io.in.req.valid := io.out.rsp.valid
  }

  // We are always ready to receive a response
  io.out.rsp.ready := true.B

}

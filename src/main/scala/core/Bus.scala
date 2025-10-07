package core

import chisel3._
import chisel3.util._

/** Generic Bus interface for memory access using DecoupledIO. This can be
  * extended or replaced with a specific protocol as needed.
  */
class BusReq(addrWidth: Int, dataWidth: Int) extends Bundle {
  val addr = UInt(addrWidth.W)
  val wdata = UInt(dataWidth.W)
  val wen = Bool()
  val ren = Bool()
}

class BusRsp(dataWidth: Int) extends Bundle {
  val data = UInt(dataWidth.W)
}

/** Standard Bus: on a valid request, the data is available in that cycle.
  */
class BusIO(addrWidth: Int, dataWidth: Int) extends Bundle {
  val req = Decoupled(new BusReq(addrWidth, dataWidth))
  val rsp = Flipped(new BusRsp(dataWidth))
}

/** Decoupled Bus: on a valid request, the receiver makes a promise to handle
  * this request. A response is generated on the response signal. This may occur
  * in the next cycle or later. The producer should be ready to accept this
  * response. It is up to the receiver to decide what to do when the producer of
  * the request is not ready for this response. It is up to the producer to keep
  * track of its own requests and which response corresponds to which request.
  */
class DecoupledBusIO(addrWidth: Int, dataWidth: Int) extends Bundle {
  val req = Decoupled(new BusReq(addrWidth, dataWidth))
  val rsp = Flipped(Decoupled(new BusRsp(dataWidth)))
}

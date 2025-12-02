package memory

import chisel3._
import core.DecoupledBusIO

class MemDemux(addrWidth: Int, dataWidth: Int, addrBound: Int) extends Module {

  val io = IO(new Bundle {
    val in = Flipped(new DecoupledBusIO(addrWidth, dataWidth));
    val outs = Vec(2, new DecoupledBusIO(addrWidth, dataWidth));
  })

  // Determine the output
  val outSel = (io.in.req.bits.addr >= addrBound.U).asUInt

  // Default connections:
  io.outs.foreach { out => out.req := DontCare; out.req.valid := false.B; out.rsp.ready := false.B }

  // Connect the req
  io.outs(outSel).req <> io.in.req

  // Connect the rsp based on previous selection
  val prevOutSel = RegInit(outSel)
  when(io.in.req.fire) { prevOutSel := outSel };
  io.in.rsp <> io.outs(prevOutSel).rsp

}

package csr

import chisel3._
import csr.CsrIO

class CsrDemux(addrBound: Int) extends Module {

  val io = IO(new Bundle {
    val in = Flipped(new CsrIO);
    val outs = Vec(2, new CsrIO);
  })

  // Determine the output
  val outSel = (io.in.req.bits.addr >= addrBound.U).asUInt

  // Default connections:
  io.outs.foreach { out => out.req := DontCare; out.req.valid := false.B }

  // Connect the req
  io.outs(outSel) <> io.in

}

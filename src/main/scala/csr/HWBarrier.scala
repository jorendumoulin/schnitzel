package csr

import chisel3._
import core.DecoupledBusIO
import chisel3.util.log2Up
import chisel3.util.RRArbiter
import core.BusReq

class HWBarrier(numInp: Int) extends Module {

  val io = IO(new Bundle {
    val ins = Vec(numInp, Flipped(new CsrIO))
    // val in = Flipped(new CsrIO)
  })

  // All inputs should be syncinc to be ready
  val sync = io.ins.map { csr => csr.req.bits.addr === 0x0.U && csr.req.valid }.reduce(_ && _)
  io.ins.foreach(_.req.ready := sync)
  io.ins.foreach(_.rsp.rdata := DontCare)

}

object HWBarrier {

  /** Instantiate an HWBarrier and wire its inputs from `inputs`. The barrier
    * width is derived from the input sequence.
    */
  def apply(inputs: Seq[CsrIO]): HWBarrier = {
    val barrier = Module(new HWBarrier(inputs.size))
    barrier.io.ins <> VecInit(inputs)
    barrier
  }
}

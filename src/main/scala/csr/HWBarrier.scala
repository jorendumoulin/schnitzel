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
  val sync = io.ins.map { csr => csr.req.bits.addr === 0x800.U && csr.req.valid }.reduce(_ && _)
  io.ins.foreach(_.req.ready := sync)
  io.ins.foreach(_.rsp.rdata := DontCare)

}

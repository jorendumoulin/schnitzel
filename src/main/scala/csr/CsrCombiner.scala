package csr

import chisel3._
import chisel3.util.log2Up
import chisel3.util.RRArbiter
import core.BusReq

class CsrCombiner(numInp: Int) extends Module {

  val io = IO(new Bundle {
    val ins = Vec(numInp, Flipped(new CsrIO))
    val out = new CsrIO
  })

  val allValid = io.ins.map(_.req.valid).reduce(_ && _)
  val allRead = io.ins.map(_.req.bits.op === CsrOp.READ).reduce(_ && _)
  val commonAddr = io.ins.head.req.bits.addr
  val allSameAddr = io.ins.map(_.req.bits.addr === commonAddr).reduce(_ && _)

  io.out.req.valid := allValid && allRead && allSameAddr
  io.out.req.bits.addr := commonAddr
  io.out.req.bits.wdata := DontCare
  io.out.req.bits.op := CsrOp.READ

  io.ins.foreach(_.req.ready := io.out.req.ready)
  io.ins.foreach(_.rsp.rdata := io.out.rsp.rdata)
}

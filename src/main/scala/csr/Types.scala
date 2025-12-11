package csr

import chisel3._
import chisel3.util.{Decoupled}

object CsrOp extends ChiselEnum {
  val READ = Value(0.U(2.W))
  val WRITE = Value(1.U(2.W))
  val SET = Value(2.U(2.W))
  val CLEAR = Value(3.U(2.W))
}

class CsrReq extends Bundle {
  val addr = UInt(12.W)
  val wdata = UInt(32.W)
  val op = CsrOp()
}

class CsrRsp extends Bundle {
  val rdata = UInt(32.W)
}

class CsrIO extends Bundle {
  val req = Decoupled(new CsrReq)
  val rsp = Input(new CsrRsp)
}

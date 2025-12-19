package csr

// Implements the shadow register CSR interface

import chisel3._
import core.DecoupledBusIO
import chisel3.util.log2Up
import chisel3.util.RRArbiter
import core.BusReq

class CsrInterface(numRegisters: Int, baseAddr: Int) extends Module {

  val io = IO(new Bundle {
    val csr = Flipped(new CsrIO)
    val vals = Vec(numRegisters, UInt(32.W))
    val start = Output(Bool())
    val done = Input(Bool())
  })

  // Send start signal / set barrier
  when(io.csr.req.valid && io.csr.req.bits.addr === (baseAddr + numRegisters).U && io.done) {
    io.csr.req.ready := true.B;
    io.start := io.csr.req.bits.wdata === 1.U;
  }.otherwise { io.start := false.B; io.csr.req.ready := false.B; }
  io.csr.rsp.rdata := DontCare

  // Shadow registers mechanism
  for (i <- 0 until numRegisters) {
    val shadowReg, valueReg = RegInit(0.U(32.W))
    when(io.csr.req.valid && io.csr.req.bits.addr === (baseAddr + i).U) {
      io.csr.req.ready := true.B;
      shadowReg := io.csr.req.bits.wdata
    }
    when(io.start) { valueReg := shadowReg }
    io.vals(i) := valueReg
  }

}

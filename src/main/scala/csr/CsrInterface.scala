package csr

// Implements the shadow register CSR interface

import chisel3._
import core.DecoupledBusIO
import core.BusReq

class CsrInterface(numRegisters: Int, baseAddr: Int) extends Module {

  val io = IO(new Bundle {
    /** CSR interface, RISC-V facing */
    val csr = Flipped(new CsrIO)
    /** Value registers, accelerator-facing */
    val vals = Output(Vec(numRegisters, UInt(32.W))) 
    /** Signal to start accelerator, single-pulse */
    val start = Output(Bool())
    /** High when accelerator is done */
    val done = Input(Bool())
  })

  // Send start signal / set barrier
  val isSyncAddr = io.csr.req.bits.addr === (baseAddr + numRegisters).U
  //val isWriteOp = io.csr.req.bits.op === CsrOp.WRITE

  // If the accelerator is done, and the CSR request is valid for the special register
  when(io.done && io.csr.req.valid && isSyncAddr) {
    // Don't stall the CPU
    io.csr.req.ready := true.B;
    // start the accelerator if the written data is exactly 0x01
    io.start := io.csr.req.bits.wdata === 1.U;
  //} .elsewhen(io.done && io.csr.req.valid && isSyncAddr) {
  //  // Don't stall the CPU
  //  io.csr.req.ready := true.B;
  //  // Don't signal a start
  //  io.start := false.B; 
  // If the accelerator is not done, and the CSR request is valid for the special register
  }.otherwise { 
    // Don't signal a start
    io.start := false.B; 
    // stall the CPU
    io.csr.req.ready := false.B; }
  // We currently don't care about the values inside the registers themselves
  io.csr.rsp.rdata := DontCare

  // Shadow registers mechanism
  for (i <- 0 until numRegisters) {
    // Instantiate a double register set
    val shadowReg, valueReg = RegInit(0.U(32.W))
    // All value register's outputs are connected to IO
    io.vals(i) := valueReg
    // If an address is written in this range, and the request is valid
    when(io.csr.req.valid && io.csr.req.bits.addr === (baseAddr + i).U) {
      // Set ready request to true
      io.csr.req.ready := true.B;
      // Store the value in the ShadowRegister
      shadowReg := io.csr.req.bits.wdata
    }
    // Upon io.start, commit all shadowregisters to the valueregisters
    when(io.start) { valueReg := shadowReg }
  }

}

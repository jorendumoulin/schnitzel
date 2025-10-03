package core

import chisel3._
import chisel3.util._

/** Basic CSR (Control and Status Register) module for RV64. Supports read and
  * write operations for a small set of CSRs.
  */
class CSRIO extends Bundle {
  val addr = Input(UInt(12.W))
  val wdata = Input(UInt(64.W))
  val rdata = Output(UInt(64.W))
  val wen = Input(Bool())
  val ren = Input(Bool())
}

class CSR extends Module {
  val io = IO(new CSRIO)

  // Define a small set of CSRs for demonstration (can be expanded)
  val mstatus = RegInit(0.U(64.W))
  val mie = RegInit(0.U(64.W))
  val mtvec = RegInit(0.U(64.W))
  val mscratch = RegInit(0.U(64.W))
  val mepc = RegInit(0.U(64.W))
  val mcause = RegInit(0.U(64.W))
  val mip = RegInit(0.U(64.W))

  // CSR address mapping (RV64 privileged spec)
  val CSR_MSTATUS = "h300".U(12.W)
  val CSR_MIE = "h304".U(12.W)
  val CSR_MTVEC = "h305".U(12.W)
  val CSR_MSCRATCH = "h340".U(12.W)
  val CSR_MEPC = "h341".U(12.W)
  val CSR_MCAUSE = "h342".U(12.W)
  val CSR_MIP = "h344".U(12.W)

  // Read logic
  io.rdata := MuxLookup(
    io.addr,
    0.U(64.W)
  )(
    Seq(
      CSR_MSTATUS -> mstatus,
      CSR_MIE -> mie,
      CSR_MTVEC -> mtvec,
      CSR_MSCRATCH -> mscratch,
      CSR_MEPC -> mepc,
      CSR_MCAUSE -> mcause,
      CSR_MIP -> mip
    )
  )

  // Write logic
  when(io.wen) {
    switch(io.addr) {
      is(CSR_MSTATUS) { mstatus := io.wdata }
      is(CSR_MIE) { mie := io.wdata }
      is(CSR_MTVEC) { mtvec := io.wdata }
      is(CSR_MSCRATCH) { mscratch := io.wdata }
      is(CSR_MEPC) { mepc := io.wdata }
      is(CSR_MCAUSE) { mcause := io.wdata }
      is(CSR_MIP) { mip := io.wdata }
    }
  }
}

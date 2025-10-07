package core

import chisel3._
import chisel3.util._

/** WriteBack module Handles the selection of the appropriate result (ALU,
  * memory, or CSR) and writes the result to the destination register.
  */
class WriteBack extends Module {
  val io = IO(new Bundle {
    val aluResult = Input(UInt(64.W)) // Result from ALU
    val memResult = Input(UInt(64.W)) // Result from memory
    val csrResult = Input(UInt(64.W)) // Result from CSR
    val memToReg = Input(Bool()) // Select memory result
    val csrToReg = Input(Bool()) // Select CSR result
    val rdWrite = Output(Bool()) // Write enable for destination register
    val rdData = Output(UInt(64.W)) // Data to write to destination register
  })

  // Select the appropriate result for write-back
  io.rdData := MuxCase(
    io.aluResult,
    Seq(
      io.memToReg -> io.memResult,
      io.csrToReg -> io.csrResult
    )
  )

  // Enable write-back when any result is valid
  io.rdWrite := io.memToReg || io.csrToReg || !io.memToReg && !io.csrToReg
}

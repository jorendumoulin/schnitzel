package core

import chisel3._
import chisel3.util._

/** InstructionFetch module Handles the instruction memory interface */
class InstructionFetch extends Module {
  val io = IO(new Bundle {
    val imem = new BusIO(CoreConfig.addrWidth, CoreConfig.instrWidth)
    val pc = Input(UInt(CoreConfig.addrWidth.W))

    val stall = Output(Bool()) // Stall the cpu when instr is invalid
    val instr = Output(UInt(CoreConfig.instrWidth.W)) // Fetched instruction
  })

  // Issue instruction memory request. We do not buffer the instruction explicitly,
  // so we are constantly sending out requests for the instruction.
  io.imem.req.valid := true.B

  // Only read instructions:
  io.imem.req.bits.wen := false.B
  io.imem.req.bits.wdata := 0.U

  // Read address is the program counter
  io.imem.req.bits.addr := io.pc

  // Stall the pipeline on invalid instruction:
  io.stall := !io.imem.req.ready

  // Instruction is the result of the imem read request
  io.instr := io.imem.rsp.data

}

package core

import chisel3._
import chisel3.util._

/** Core
  *
  * Stub for a single-cycle, single-issue RV64IM RISC-V CPU core. This module
  * will be expanded to support instruction fetch, decode, execute, memory
  * access, and CSR operations.
  */
class CoreIO extends Bundle {
  // Generic bus interface for instruction and data memory using DecoupledIO
  val imem = new BusIO // Instruction memory interface
  val dmem = new BusIO // Data memory interface

  // Optional: external interrupt lines, reset, etc.
  val extInterrupt = Input(Bool())
  val timerInterrupt = Input(Bool())
  val softwareInterrupt = Input(Bool())
}

class Core extends Module {
  val io = IO(new CoreIO)

  // === Pipeline Registers (Single-Cycle: all logic in one cycle) ===
  // PC register
  val pc = RegInit(0.U(64.W))

  // Register file
  val regFile = Module(new RegisterFile)

  // CSR unit
  val csr = Module(new CSR)

  // Decoder
  val decoder = Module(new Decoder)

  // ALU
  val alu = Module(new ALU)

  // === Instruction Fetch ===
  io.imem.req.valid := true.B
  io.imem.req.bits.addr := pc
  io.imem.req.bits.wdata := 0.U
  io.imem.req.bits.wen := false.B
  io.imem.req.bits.ren := true.B

  val instr = io.imem.rdata

  // === Decode ===
  decoder.io.instr := instr

  // === Register Read ===
  regFile.io.rs1Addr := decoder.io.rs1
  regFile.io.rs2Addr := decoder.io.rs2
  regFile.io.rdAddr := decoder.io.rd

  // === ALU Operation ===
  alu.io.op := decoder.io.aluOp
  alu.io.srcA := regFile.io.rs1Data
  alu.io.srcB := Mux(
    decoder.io.memEn || decoder.io.memWe,
    regFile.io.rs2Data,
    Mux(
      decoder.io.opcode === Opcodes.OP_LUI,
      instr(31, 12).asUInt,
      regFile.io.rs2Data
    )
  )

  // === CSR Operation ===
  csr.io.addr := decoder.io.csrAddr
  csr.io.wdata := regFile.io.rs1Data
  csr.io.wen := decoder.io.csrEn && (decoder.io.csrOp === Opcodes.CSR_RW || decoder.io.csrOp === Opcodes.CSR_RWI)
  csr.io.ren := decoder.io.csrEn

  // === Memory Access ===
  io.dmem.req.valid := decoder.io.memEn || decoder.io.memWe
  io.dmem.req.bits.addr := alu.io.result
  io.dmem.req.bits.wdata := regFile.io.rs2Data
  io.dmem.req.bits.wen := decoder.io.memWe
  io.dmem.req.bits.ren := decoder.io.memEn

  // === Writeback ===
  val wbData = Mux(
    decoder.io.csrEn,
    csr.io.rdata,
    Mux(decoder.io.memEn, io.dmem.rdata, alu.io.result)
  )
  regFile.io.rdData := wbData
  regFile.io.rdWrite := decoder.io.rdEn

  // === PC Update ===
  // Branch/jump logic
  val pcNext = Wire(UInt(64.W))
  pcNext := pc + 4.U

  when(decoder.io.opcode === Opcodes.OP_BRANCH && alu.io.cmpOut) {
    // Branch taken: calculate target
    val imm =
      Cat(instr(31), instr(7), instr(30, 25), instr(11, 8), 0.U(1.W)).asSInt
    pcNext := (pc.asSInt + imm).asUInt
  }.elsewhen(decoder.io.opcode === Opcodes.OP_JAL) {
    val imm =
      Cat(instr(31), instr(19, 12), instr(20), instr(30, 21), 0.U(1.W)).asSInt
    pcNext := (pc.asSInt + imm).asUInt
  }.elsewhen(decoder.io.opcode === Opcodes.OP_JALR) {
    val imm = instr(31, 20).asSInt
    pcNext := (regFile.io.rs1Data.asSInt + imm).asUInt & (~1.U(64.W))
  }

  pc := pcNext

  // === Interrupt Handling (stub) ===
  // To be implemented: handle external, timer, and software interrupts
}

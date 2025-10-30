package core

import chisel3._
import chisel3.util._
import chisel3.util.Decoupled

/** Core: A basic RV64IM CPU implementation */
class Core extends Module {
  val io = IO(new Bundle {
    val imem = new BusIO(CoreConfig.addrWidth, CoreConfig.instrWidth)
    val dmem = new BusIO(CoreConfig.addrWidth, CoreConfig.dataWidth)
  })

  // ============================
  // === Module Instantiation ===
  // ============================

  // === Instruction Fetch ===
  val pc = RegInit(0.U(CoreConfig.addrWidth.W))
  val fetch = Module(new InstructionFetch)
  fetch.io.pc := pc
  fetch.io.imem <> io.imem

  // === Decode ===
  val decoder = Module(new Decoder)
  decoder.io.instr := fetch.io.instr

  val regFile = Module(new RegisterFile)
  regFile.io.rs1Addr := decoder.io.rs1
  regFile.io.rs2Addr := decoder.io.rs2
  regFile.io.rdAddr := decoder.io.rd
  regFile.io.rdData := 0.U
  regFile.io.rdWrite := decoder.io.rdEn

  // === Execute ===
  val alu = Module(new ALU)
  alu.io.op := decoder.io.aluOp
  alu.io.srcA := regFile.io.rs1Data
  alu.io.srcB := Mux( // imm value on mem acess or csr, else rs2
    decoder.io.memAccessEn || decoder.io.csrEn,
    decoder.io.immValue,
    regFile.io.rs2Data
  )

  // === Memory ===
  val memory = Module(new MemoryAccess)
  memory.io.dmem <> io.dmem
  memory.io.memEn := decoder.io.memAccessEn
  memory.io.memWe := decoder.io.memWriteEn
  memory.io.addr := alu.io.result
  memory.io.wdata := regFile.io.rs2Data
  val memData = memory.io.rdata

  // === Writeback ===
  val writeBack = Module(new WriteBack)
  writeBack.io.aluResult := alu.io.result
  writeBack.io.memResult := memData
  writeBack.io.memToReg := decoder.io.memAccessEn
  writeBack.io.csrToReg := decoder.io.csrEn
  regFile.io.rdData := writeBack.io.rdData

  // === Extras ===
  val csr = Module(new CSR)
  csr.io.addr := decoder.io.immValue
  csr.io.wdata := regFile.io.rs2Data
  csr.io.wen := decoder.io.csrEn && decoder.io.memWriteEn
  csr.io.ren := decoder.io.csrEn && !decoder.io.memWriteEn
  writeBack.io.csrResult := csr.io.rdata

  // === PC Update ===
  when(!fetch.io.stall) {
    pc := pc + 4.U
  }

}

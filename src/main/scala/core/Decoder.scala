package core

import chisel3._
import chisel3.util._
import core.Insts
import core.Opcodes._

/** Decoder for RV64IM instructions. Decodes instruction bits into control
  * signals for the datapath, ALU, register file, and CSR logic.
  */
class DecoderIO extends Bundle {
  val instr = Input(UInt(32.W))
  val opcode = Output(UInt(7.W))
  val funct3 = Output(UInt(3.W))
  val funct7 = Output(UInt(7.W))
  val rs1 = Output(UInt(5.W))
  val rs2 = Output(UInt(5.W))
  val rd = Output(UInt(5.W))

  // Control signals
  val aluOp = Output(UInt(6.W)) // ALU operation selector
  val memAccessEn = Output(Bool()) // Memory access enable
  val memWriteEn = Output(Bool()) // Memory write enable
  val csrEn = Output(Bool()) // CSR operation enable
  val csrOpSel = Output(UInt(3.W)) // CSR operation selector
  val immValue = Output(UInt(12.W)) // Immediate value
  val rdEn = Output(Bool()) // Register write enable
}

class Decoder extends Module {
  val io = IO(new DecoderIO)

  // Extract fields from instruction
  val instr = io.instr
  io.opcode := instr(6, 0)
  io.rd := instr(11, 7)
  io.funct3 := instr(14, 12)
  io.rs1 := instr(19, 15)
  io.rs2 := instr(24, 20)
  io.funct7 := instr(31, 25)

  // Default control signals
  io.aluOp := 0.U
  io.memAccessEn := false.B
  io.memWriteEn := false.B
  io.csrEn := false.B
  io.csrOpSel := 0.U
  io.immValue := 0.U
  io.rdEn := false.B

  // Instruction decode logic
  // RV64IM: LUI, AUIPC, JAL, JALR, BEQ, BNE, BLT, BGE, BLTU, BGEU, LB, LH, LW, LBU, LHU, SB, SH, SW, ADDI, SLTI, SLTIU, XORI, ORI, ANDI, SLLI, SRLI, SRAI, ADD, SUB, SLL, SLT, SLTU, XOR, SRL, SRA, OR, AND, LWU, LD, SD, ADDIW, SLLIW, SRLIW, SRAIW, ADDW, SUBW, SLLW, SRLW, SRAW, MUL, MULH, MULHSU, MULHU, DIV, DIVU, REM, REMU, CSRRW, CSRRS, CSRRC, CSRRWI, CSRRSI, CSRRCI

  // Use ALU and CSR operation codes from Opcodes.scala

  // Decode main instruction types
  switch(io.opcode) {
    is(OP_LUI) {
      io.aluOp := ALU_COPY_B
      io.rdEn := true.B
    }
    is(OP_AUIPC) {
      io.aluOp := ALU_ADD
      io.rdEn := true.B
    }
    is(OP_JAL) {
      io.aluOp := ALU_ADD
      io.rdEn := true.B
    }
    is(OP_JALR) {
      io.aluOp := ALU_ADD
      io.rdEn := true.B
    }
    is(OP_BRANCH) {
      io.aluOp := ALU_SUB
      io.rdEn := false.B
    }
    is(OP_LOAD) {
      io.aluOp := ALU_ADD
      io.memAccessEn := true.B
      io.rdEn := true.B
    }
    is(OP_STORE) {
      io.aluOp := ALU_ADD
      io.memAccessEn := true.B
      io.memWriteEn := true.B
      io.rdEn := false.B
    }
    is(OP_IMM) {
      switch(io.funct3) {
        is(F3_ADD_SUB) { io.aluOp := ALU_ADD; io.rdEn := true.B } // ADDI
        is(F3_SLT) { io.aluOp := ALU_SLT; io.rdEn := true.B } // SLTI
        is(F3_SLTU) { io.aluOp := ALU_SLTU; io.rdEn := true.B } // SLTIU
        is(F3_XOR) { io.aluOp := ALU_XOR; io.rdEn := true.B } // XORI
        is(F3_OR) { io.aluOp := ALU_OR; io.rdEn := true.B } // ORI
        is(F3_AND) { io.aluOp := ALU_AND; io.rdEn := true.B } // ANDI
        is(F3_SLL) { io.aluOp := ALU_SLL; io.rdEn := true.B } // SLLI
        is(F3_SRL_SRA) {
          when(io.funct7 === F7_SRL) {
            io.aluOp := ALU_SRL; io.rdEn := true.B
          } // SRLI
          when(io.funct7 === F7_SRA) {
            io.aluOp := ALU_SRA; io.rdEn := true.B
          } // SRAI
        }
      }
    }
    is(OP_REG) {
      switch(io.funct3) {
        is(F3_ADD_SUB) {
          when(io.funct7 === F7_ADD) {
            io.aluOp := ALU_ADD; io.rdEn := true.B
          } // ADD
          when(io.funct7 === F7_SUB) {
            io.aluOp := ALU_SUB; io.rdEn := true.B
          } // SUB
          when(io.funct7 === F7_MUL) {
            io.aluOp := ALU_MUL; io.rdEn := true.B
          } // MUL
        }
        is(F3_SLL) { io.aluOp := ALU_SLL; io.rdEn := true.B }
        is(F3_SLT) { io.aluOp := ALU_SLT; io.rdEn := true.B }
        is(F3_SLTU) { io.aluOp := ALU_SLTU; io.rdEn := true.B }
        is(F3_XOR) { io.aluOp := ALU_XOR; io.rdEn := true.B }
        is(F3_SRL_SRA) {
          when(io.funct7 === F7_SRL) { io.aluOp := ALU_SRL; io.rdEn := true.B }
          when(io.funct7 === F7_SRA) { io.aluOp := ALU_SRA; io.rdEn := true.B }
        }
        is(F3_OR) { io.aluOp := ALU_OR; io.rdEn := true.B }
        is(F3_AND) { io.aluOp := ALU_AND; io.rdEn := true.B }
      }
    }
    is(OP_SYSTEM) {
      io.csrEn := true.B
      io.rdEn := true.B
      io.immValue := instr(31, 20)
      switch(io.funct3) {
        is("b001".U) { io.csrOpSel := CSR_RW } // CSRRW
        is("b010".U) { io.csrOpSel := CSR_RS } // CSRRS
        is("b011".U) { io.csrOpSel := CSR_RC } // CSRRC
        is("b101".U) { io.csrOpSel := CSR_RWI } // CSRRWI
        is("b110".U) { io.csrOpSel := CSR_RSI } // CSRRSI
        is("b111".U) { io.csrOpSel := CSR_RCI } // CSRRCI
      }
    }
    // Add more cases for RV64I-specific and M-extension instructions as needed
  }
}

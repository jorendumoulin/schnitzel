package core

import chisel3._
import chisel3.util._

/**
 * Named constants for RISC-V opcodes, funct3, funct7, ALU operations, and CSR operations.
 * Use these in the decoder and datapath for clarity and maintainability.
 */
object Opcodes {
  // RISC-V base opcodes (7 bits)
  val OP_LUI      = "b0110111".U(7.W)
  val OP_AUIPC    = "b0010111".U(7.W)
  val OP_JAL      = "b1101111".U(7.W)
  val OP_JALR     = "b1100111".U(7.W)
  val OP_BRANCH   = "b1100011".U(7.W)
  val OP_LOAD     = "b0000011".U(7.W)
  val OP_STORE    = "b0100011".U(7.W)
  val OP_IMM      = "b0010011".U(7.W)
  val OP_REG      = "b0110011".U(7.W)
  val OP_IMMW     = "b0011011".U(7.W) // RV64I
  val OP_REGW     = "b0111011".U(7.W) // RV64I
  val OP_MISC_MEM = "b0001111".U(7.W)
  val OP_SYSTEM   = "b1110011".U(7.W)

  // Funct3 values (3 bits)
  val F3_ADD_SUB  = "b000".U(3.W)
  val F3_SLL      = "b001".U(3.W)
  val F3_SLT      = "b010".U(3.W)
  val F3_SLTU     = "b011".U(3.W)
  val F3_XOR      = "b100".U(3.W)
  val F3_SRL_SRA  = "b101".U(3.W)
  val F3_OR       = "b110".U(3.W)
  val F3_AND      = "b111".U(3.W)

  // Branch funct3
  val F3_BEQ      = "b000".U(3.W)
  val F3_BNE      = "b001".U(3.W)
  val F3_BLT      = "b100".U(3.W)
  val F3_BGE      = "b101".U(3.W)
  val F3_BLTU     = "b110".U(3.W)
  val F3_BGEU     = "b111".U(3.W)

  // Load funct3
  val F3_LB       = "b000".U(3.W)
  val F3_LH       = "b001".U(3.W)
  val F3_LW       = "b010".U(3.W)
  val F3_LBU      = "b100".U(3.W)
  val F3_LHU      = "b101".U(3.W)
  val F3_LWU      = "b110".U(3.W)
  val F3_LD       = "b011".U(3.W)

  // Store funct3
  val F3_SB       = "b000".U(3.W)
  val F3_SH       = "b001".U(3.W)
  val F3_SW       = "b010".U(3.W)
  val F3_SD       = "b011".U(3.W)

  // Funct7 values (7 bits)
  val F7_ADD      = "b0000000".U(7.W)
  val F7_SUB      = "b0100000".U(7.W)
  val F7_SRA      = "b0100000".U(7.W)
  val F7_SRL      = "b0000000".U(7.W)
  val F7_SLL      = "b0000000".U(7.W)
  val F7_MUL      = "b0000001".U(7.W)

  // ALU operation codes (6 bits)
  val ALU_ADD     = 0.U(6.W)
  val ALU_SUB     = 1.U(6.W)
  val ALU_AND     = 2.U(6.W)
  val ALU_OR      = 3.U(6.W)
  val ALU_XOR     = 4.U(6.W)
  val ALU_SLT     = 5.U(6.W)
  val ALU_SLTU    = 6.U(6.W)
  val ALU_SLL     = 7.U(6.W)
  val ALU_SRL     = 8.U(6.W)
  val ALU_SRA     = 9.U(6.W)
  val ALU_COPY_B  = 10.U(6.W) // For LUI, loads, CSR, etc.
  val ALU_MUL     = 11.U(6.W)
  val ALU_MULH    = 12.U(6.W)
  val ALU_MULHSU  = 13.U(6.W)
  val ALU_MULHU   = 14.U(6.W)
  val ALU_DIV     = 15.U(6.W)
  val ALU_DIVU    = 16.U(6.W)
  val ALU_REM     = 17.U(6.W)
  val ALU_REMU    = 18.U(6.W)

  // CSR operation codes (3 bits)
  val CSR_RW      = 1.U(3.W)
  val CSR_RS      = 2.U(3.W)
  val CSR_RC      = 3.U(3.W)
  val CSR_RWI     = 4.U(3.W)
  val CSR_RSI     = 5.U(3.W)
  val CSR_RCI     = 6.U(3.W)
}

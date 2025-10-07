package core

import chisel3._
import chisel3.util._

import core.Opcodes._

/** ALU for RV64IM core. Implements arithmetic, logical, comparison, and
  * M-extension operations.
  */
class ALU extends Module {
  val io = IO(new Bundle {
    val op = Input(UInt(6.W)) // ALU operation selector
    val srcA = Input(UInt(CoreConfig.dataWidth.W)) // First operand
    val srcB = Input(UInt(CoreConfig.dataWidth.W)) // Second operand
    val result = Output(UInt(CoreConfig.dataWidth.W)) // ALU result
    val cmpOut = Output(Bool()) // Comparison result (for branches)
  })

  // Arithmetic operations
  val add = io.srcA + io.srcB
  val sub = io.srcA - io.srcB

  // Logical operations
  val and = io.srcA & io.srcB
  val or = io.srcA | io.srcB
  val xor = io.srcA ^ io.srcB

  // Shift operations
  val sll = io.srcA << io.srcB(5, 0)
  val srl = io.srcA >> io.srcB(5, 0)
  val sra = (io.srcA.asSInt >> io.srcB(5, 0)).asUInt

  // Set-less-than operations
  val slt = io.srcA.asSInt < io.srcB.asSInt
  val sltu = io.srcA < io.srcB

  // M-extension (multiplication/division)
  val mul = io.srcA * io.srcB
  val mulh = ((io.srcA.asSInt * io.srcB.asSInt) >> 64).asUInt
  val mulhu = ((io.srcA * io.srcB) >> 64).asUInt
  val mulhsu = ((io.srcA.asSInt * io.srcB) >> 64).asUInt

  val div = Mux(
    io.srcB === 0.U,
    BigInt("FFFFFFFFFFFFFFFF", 16).U(64.W),
    (io.srcA.asSInt / io.srcB.asSInt).asUInt
  )
  val divu = Mux(
    io.srcB === 0.U,
    BigInt("FFFFFFFFFFFFFFFF", 16).U(64.W),
    io.srcA / io.srcB
  )
  val rem =
    Mux(io.srcB === 0.U, io.srcA, (io.srcA.asSInt % io.srcB.asSInt).asUInt)
  val remu = Mux(io.srcB === 0.U, io.srcA, io.srcA % io.srcB)

  // Default outputs
  io.result := 0.U
  io.cmpOut := false.B

  switch(io.op) {
    is(ALU_ADD) { io.result := add }
    is(ALU_SUB) { io.result := sub }
    is(ALU_AND) { io.result := and }
    is(ALU_OR) { io.result := or }
    is(ALU_XOR) { io.result := xor }
    is(ALU_SLT) { io.result := slt.asUInt }
    is(ALU_SLTU) { io.result := sltu.asUInt }
    is(ALU_SLL) { io.result := sll }
    is(ALU_SRL) { io.result := srl }
    is(ALU_SRA) { io.result := sra }
    is(ALU_COPY_B) { io.result := io.srcB }
    is(ALU_MUL) { io.result := mul }
    is(ALU_MULH) { io.result := mulh }
    is(ALU_MULHSU) { io.result := mulhsu }
    is(ALU_MULHU) { io.result := mulhu }
    is(ALU_DIV) { io.result := div }
    is(ALU_DIVU) { io.result := divu }
    is(ALU_REM) { io.result := rem }
    is(ALU_REMU) { io.result := remu }
  }

  // Comparison output for branches
  io.cmpOut := MuxLookup(io.op, false.B)(
    Seq(
      ALU_SLT -> slt,
      ALU_SLTU -> sltu,
      ALU_SUB -> (add === 0.U)
    )
  )
}

package core

import chisel3._
import chisel3.util._

/** RegisterFile stub for RV64IM core. 32 general-purpose registers (x0-x31),
  * each 64 bits wide. x0 is always zero.
  */
class RegisterFileIO extends Bundle {
  val rs1Addr = Input(UInt(5.W))
  val rs2Addr = Input(UInt(5.W))
  val rdAddr = Input(UInt(5.W))
  val rdData = Input(UInt(CoreConfig.dataWidth.W))
  val rdWrite = Input(Bool())
  val rs1Data = Output(UInt(CoreConfig.dataWidth.W))
  val rs2Data = Output(UInt(CoreConfig.dataWidth.W))
}

class RegisterFile extends Module {
  val io = IO(new RegisterFileIO)

  // 32 registers
  val regs = RegInit(VecInit(Seq.fill(32)(0.U(CoreConfig.dataWidth.W))))

  // Read ports
  io.rs1Data := Mux(io.rs1Addr === 0.U, 0.U, regs(io.rs1Addr))
  io.rs2Data := Mux(io.rs2Addr === 0.U, 0.U, regs(io.rs2Addr))

  // Write port
  when(io.rdWrite && (io.rdAddr =/= 0.U)) {
    regs(io.rdAddr) := io.rdData
  }
}

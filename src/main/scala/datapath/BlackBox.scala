package datapath

import chisel3._
import chisel3.util._

class acc1_array(numPEs: Int = 4, dataWidth: Int = 64) extends BlackBox() with HasBlackBoxPath {

  val io = IO(new Bundle {
    val data_0 = Input(Vec(numPEs, UInt(dataWidth.W)))
    val data_1 = Input(Vec(numPEs, UInt(dataWidth.W)))
    val switch_0 = Input(UInt(2.W))
    val out_0 = Output(Vec(numPEs, UInt(dataWidth.W)))
  })

  addPath("src/main/resources/phs/acc1_array.sv")
}

class AluBlackBoxArrayWrapper(numPEs: Int = 4, dataWidth: Int = 64) extends Module {
  val io = IO(new Bundle {
    val A_in = Flipped(Decoupled(Vec(numPEs, UInt(dataWidth.W))))
    val B_in = Flipped(Decoupled(Vec(numPEs, UInt(dataWidth.W))))
    val C_out = Decoupled(Vec(numPEs, UInt(dataWidth.W)))
    val sel = Input(UInt(2.W))
  })

  // Instantiate the MLIR-generated BlackBox
  val bb = Module(new acc1_array(numPEs, dataWidth))
  // Logic to handle Decoupled handshaking
  val canProcess = io.C_out.ready
  io.A_in.ready := canProcess
  io.B_in.ready := canProcess
  io.C_out.valid := io.A_in.valid && io.B_in.valid

  // Connect wires to the BlackBox
  bb.io.data_0 := io.A_in.bits
  bb.io.data_1 := io.B_in.bits
  bb.io.switch_0 := io.sel
  io.C_out.bits := bb.io.out_0
}

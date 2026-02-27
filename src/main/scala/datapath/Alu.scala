package datapath

import chisel3._
import chisel3.util.MuxLookup
import circt.stage.ChiselStage
import chisel3.util.Decoupled

class AluPE(dataWidth: Int = 32) extends Module {
  val io = IO(new Bundle {
    val A = Input(UInt((dataWidth).W))
    val B = Input(UInt((dataWidth).W))
    val sel = Input(UInt(2.W))
    val C = Output(UInt((dataWidth).W))
  })

  io.C := MuxLookup(io.sel, 0.U)(
    Seq(
      0.U -> (io.A + io.B),
      1.U -> (io.A - io.B),
      2.U -> (io.A * io.B),
      3.U -> (io.A ^ io.B)
    )
  )

}

class AluArray(numPEs: Int = 4, dataWidth: Int = 32) extends Module {
  val io = IO(new Bundle {
    val A_in = Flipped(Decoupled(Vec(numPEs, UInt(dataWidth.W))))
    val B_in = Flipped(Decoupled(Vec(numPEs, UInt(dataWidth.W))))
    val C_out = Decoupled(Vec(numPEs, UInt(dataWidth.W)))
    val sel = Input(UInt(2.W))
  })
  val canProcess = io.C_out.ready
  io.A_in.ready := canProcess
  io.B_in.ready := canProcess
  io.C_out.valid := io.A_in.valid && io.B_in.valid

  val pes = Seq.fill(numPEs)(Module(new AluPE(dataWidth)))
  for (i <- 0 until numPEs) {
    pes(i).io.sel := io.sel // Global control connected to every PE
    pes(i).io.A := io.A_in.bits(i) // Individual data A
    pes(i).io.B := io.B_in.bits(i) // Individual data B
    io.C_out.bits(i) := pes(i).io.C // Individual output C
  }
}

package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import csr.CsrIO
import csr.CsrInterface
import datapath.AluArray
import config.AluConfig
import config.AluWrapper

// ALU Accelerator: streamer <-> datapath <-> streamer
// Supports normal mode (C = f(A, B)) and readWrite mode (C = f(A, C_old)) for reductions
class AluAccelerator(addrWidth: Int, dataWidth: Int) extends Module {

  val parallelUnroll = 4 // Hardcode spatial unrolling
  val numPorts = parallelUnroll

  // warning: using this to reinterpret the vec of values, results in the
  // opposite ordering of signals as they are presented here:
  // additionally, all signals here should be 32 bits.
  class CsrVals extends Bundle {
    val aStreamerConfig = new AffineAguConfig(1, Seq(parallelUnroll))
    val bStreamerConfig = new AffineAguConfig(1, Seq(parallelUnroll))
    val cStreamerConfig = new AffineAguConfig(2, Seq(parallelUnroll)) // 2 temporal dims for reduction
    val select = UInt(32.W)
    val mode = UInt(32.W) // 0 = normal (C writes only), 1 = readWrite (reduction/in-place)
    def numRegs =
      aStreamerConfig.numRegs + bStreamerConfig.numRegs + cStreamerConfig.numRegs + 2
  }

  val io = IO(new Bundle {
    val aData = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val bData = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val cData = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val csr = Flipped(new CsrIO)
  })

  val csrItf = Module(new CsrInterface((new CsrVals).numRegs, 0x900))
  csrItf.io.csr <> io.csr
  val csrVals = VecInit(csrItf.io.vals.reverse).asTypeOf(new CsrVals)
  dontTouch(csrVals)

  val aluArray = Module(new AluArray(parallelUnroll, dataWidth))
  val truncated_sel = csrVals.select.asTypeOf(UInt(2.W))
  aluArray.io.sel := truncated_sel

  val readWriteMode = csrVals.mode(0)

  val queueDepth = 3

  // A streamer: always reads from TCDM
  val aStreamer = Module(new Streamer(1, Seq(parallelUnroll), queueDepth, addrWidth, dataWidth));
  aStreamer.io.tcdmReqs <> io.aData
  aStreamer.io.config := csrVals.aStreamerConfig
  aStreamer.io.start := csrItf.io.start
  aStreamer.io.writeData := DontCare
  aStreamer.io.dir := StreamerDir.read
  aStreamer.io.readData.valid <> aluArray.io.A_in.valid
  aStreamer.io.readData.ready <> aluArray.io.A_in.ready
  aluArray.io.A_in.bits := aStreamer.io.readData.bits.asTypeOf(Vec(parallelUnroll, UInt(dataWidth.W)))

  // B streamer: reads from TCDM, only active in normal mode
  val bStreamer = Module(new Streamer(1, Seq(parallelUnroll), queueDepth, addrWidth, dataWidth));
  bStreamer.io.tcdmReqs <> io.bData
  bStreamer.io.config := csrVals.bStreamerConfig
  bStreamer.io.start := csrItf.io.start && !readWriteMode
  bStreamer.io.writeData := DontCare
  bStreamer.io.dir := StreamerDir.read

  // C streamer: 2 temporal dims, supports write (normal) and readWrite (reduction)
  val cStreamer = Module(new Streamer(2, Seq(parallelUnroll), queueDepth, addrWidth, dataWidth));
  cStreamer.io.tcdmReqs <> io.cData
  cStreamer.io.config := csrVals.cStreamerConfig
  cStreamer.io.start := csrItf.io.start

  // C streamer direction depends on mode
  when(readWriteMode) {
    cStreamer.io.dir := StreamerDir.readWrite
  }.otherwise {
    cStreamer.io.dir := StreamerDir.write
  }

  // ALU C_out always drives C streamer writeData
  cStreamer.io.writeData.valid := aluArray.io.C_out.valid
  cStreamer.io.writeData.bits := aluArray.io.C_out.bits.asTypeOf(UInt((dataWidth * parallelUnroll).W))
  aluArray.io.C_out.ready := cStreamer.io.writeData.ready

  // ALU B_in: from B streamer (normal) or C streamer readData (readWrite)
  val cReadVec = cStreamer.io.readData.bits.asTypeOf(Vec(parallelUnroll, UInt(dataWidth.W)))
  when(readWriteMode) {
    aluArray.io.B_in.valid := cStreamer.io.readData.valid
    aluArray.io.B_in.bits := cReadVec
    cStreamer.io.readData.ready := aluArray.io.B_in.ready
    bStreamer.io.readData.ready := false.B
  }.otherwise {
    aluArray.io.B_in.valid := bStreamer.io.readData.valid
    aluArray.io.B_in.bits := bStreamer.io.readData.bits.asTypeOf(Vec(parallelUnroll, UInt(dataWidth.W)))
    bStreamer.io.readData.ready := aluArray.io.B_in.ready
    cStreamer.io.readData.ready := false.B
  }

  csrItf.io.done := cStreamer.io.done

  def getConfig = AluWrapper("alu", AluConfig())
}

package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import csr.CsrIO
import csr.CsrInterface
import datapath.AluArray
import config.AluConfig
import config.AluWrapper

// DMA instantiates streamer <-> datapath <-> streamer
//
class AluAccelerator(addrWidth: Int, dataWidth: Int) extends Module {

  val parallelUnroll = 4 // Hardcode spatial unrolling
  val numPorts = parallelUnroll

  // warning: using this to reinterpret the vec of values, results in the
  // opposite ordering of signals as they are presented here:
  // additionally, all signals here should be 32 bits.
  class CsrVals extends Bundle {
    val aStreamerConfig = new AffineAguConfig(1, Seq(parallelUnroll))
    val bStreamerConfig = new AffineAguConfig(1, Seq(parallelUnroll))
    val cStreamerConfig = new AffineAguConfig(1, Seq(parallelUnroll))
    val select = Input(UInt(32.W))
    def numRegs =
      aStreamerConfig.numRegs + bStreamerConfig.numRegs + cStreamerConfig.numRegs + 1 // one extra for select
  }

  val io = IO(new Bundle {
    val aData = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val bData = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val cData = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val csr = Flipped(new CsrIO)
  })

  val csrItf = Module(new CsrInterface((new CsrVals).numRegs, 0))
  csrItf.io.csr <> io.csr
  val csrVals = VecInit(csrItf.io.vals.reverse).asTypeOf(new CsrVals)
  dontTouch(csrVals)

  val aluArray = Module(new AluArray(parallelUnroll, dataWidth))
  val truncated_sel = csrVals.select.asTypeOf(UInt(2.W))
  aluArray.io.sel := truncated_sel

  val queueDepth = 3
  // Use streamers for tcdm requests
  val aStreamer = Module(new Streamer(1, Seq(parallelUnroll), queueDepth, addrWidth, dataWidth));
  aStreamer.io.tcdmReqs <> io.aData
  aStreamer.io.config := csrVals.aStreamerConfig
  aStreamer.io.start := csrItf.io.start
  aStreamer.io.read.valid <> aluArray.io.A_in.valid
  aStreamer.io.read.ready <> aluArray.io.A_in.ready
  aStreamer.io.write := DontCare
  aStreamer.io.dir := StreamerDir.read
  aluArray.io.A_in.bits := aStreamer.io.read.bits.asTypeOf(Vec(parallelUnroll, UInt(dataWidth.W)))

  val bStreamer = Module(new Streamer(1, Seq(parallelUnroll), queueDepth, addrWidth, dataWidth));
  bStreamer.io.tcdmReqs <> io.bData
  bStreamer.io.config := csrVals.bStreamerConfig
  bStreamer.io.start := csrItf.io.start
  bStreamer.io.read.valid <> aluArray.io.B_in.valid
  bStreamer.io.read.ready <> aluArray.io.B_in.ready
  bStreamer.io.write := DontCare
  bStreamer.io.dir := StreamerDir.read
  aluArray.io.B_in.bits := bStreamer.io.read.bits.asTypeOf(Vec(parallelUnroll, UInt(dataWidth.W)))

  val cStreamer = Module(new Streamer(1, Seq(parallelUnroll), queueDepth, addrWidth, dataWidth));
  cStreamer.io.tcdmReqs <> io.cData
  cStreamer.io.config := csrVals.cStreamerConfig
  cStreamer.io.start := csrItf.io.start
  cStreamer.io.write.valid <> aluArray.io.C_out.valid
  cStreamer.io.write.ready <> aluArray.io.C_out.ready
  cStreamer.io.write.bits := aluArray.io.C_out.bits.asTypeOf(UInt((dataWidth * parallelUnroll).W))
  cStreamer.io.read := DontCare
  cStreamer.io.dir := StreamerDir.write
  csrItf.io.done := cStreamer.io.done

  // In AluAccelerator.scala
  def getConfig = AluWrapper("alu", AluConfig())
  // def getConfig: AcceleratorWrapper = AluWrapper: AcceleratorWrapper
}

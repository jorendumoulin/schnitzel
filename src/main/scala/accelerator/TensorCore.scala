package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import csr.CsrIO
import csr.CsrInterface
import datapath.AluArray
import config.TensorCoreConfig

class TensorCore(addrWidth: Int, dataWidth: Int) extends Module {

  // warning: using this to reinterpret the vec of values, results in the
  // opposite ordering of signals as they are presented here:
  // additionally, all signals here should be 32 bits.
  class CsrVals extends Bundle {
    val aStreamerConfig = new AffineAguConfig(6, Seq(8))
    val bStreamerConfig = new AffineAguConfig(6, Seq(8))
    val cStreamerConfig = new AffineAguConfig(6, Seq(8, 4))
    def numRegs = aStreamerConfig.numRegs + bStreamerConfig.numRegs + cStreamerConfig.numRegs
  }

  val io = IO(new Bundle {
    val aData = Vec(8, new DecoupledBusIO(addrWidth, dataWidth));
    val bData = Vec(8, new DecoupledBusIO(addrWidth, dataWidth));
    val cData = Vec(32, new DecoupledBusIO(addrWidth, dataWidth));
    val csr = Flipped(new CsrIO)
  })

  val csrItf = Module(new CsrInterface((new CsrVals).numRegs, 0x900))
  csrItf.io.csr <> io.csr
  val csrVals = VecInit(csrItf.io.vals.reverse).asTypeOf(new CsrVals)
  dontTouch(csrVals)

  val aStreamer = Module(new Streamer(6, Seq(8), 3, addrWidth, dataWidth));
  val bStreamer = Module(new Streamer(6, Seq(8), 3, addrWidth, dataWidth));
  val cStreamer = Module(new Streamer(6, Seq(8, 4), 3, addrWidth, dataWidth));

  aStreamer.io.tcdmReqs <> io.aData
  aStreamer.io.config := csrVals.aStreamerConfig
  aStreamer.io.spatialDimMask := 0.U.asTypeOf(aStreamer.io.spatialDimMask)
  aStreamer.io.start := csrItf.io.start
  aStreamer.io.writeData := DontCare
  aStreamer.io.dir := StreamerDir.read
  aStreamer.io.readData.ready := bStreamer.io.readData.valid && cStreamer.io.readData.valid && cStreamer.io.writeData.ready

  val aMat = aStreamer.io.readData.bits.asTypeOf(Vec(8, Vec(8, SInt(8.W))))

  bStreamer.io.tcdmReqs <> io.bData
  bStreamer.io.config := csrVals.bStreamerConfig
  bStreamer.io.spatialDimMask := 0.U.asTypeOf(bStreamer.io.spatialDimMask)
  bStreamer.io.start := csrItf.io.start
  bStreamer.io.writeData := DontCare
  bStreamer.io.dir := StreamerDir.read
  bStreamer.io.readData.ready := aStreamer.io.readData.valid && cStreamer.io.readData.valid && cStreamer.io.writeData.ready

  val bMat = cStreamer.io.readData.bits.asTypeOf(Vec(8, Vec(8, SInt(8.W))))

  cStreamer.io.tcdmReqs <> io.cData
  cStreamer.io.config := csrVals.cStreamerConfig
  cStreamer.io.spatialDimMask := 0.U.asTypeOf(cStreamer.io.spatialDimMask)
  cStreamer.io.start := csrItf.io.start
  cStreamer.io.dir := StreamerDir.readWrite
  cStreamer.io.readData.ready := aStreamer.io.readData.valid && cStreamer.io.readData.valid && cStreamer.io.writeData.ready
  cStreamer.io.writeData.valid := aStreamer.io.readData.fire && bStreamer.io.readData.fire && cStreamer.io.readData.fire

  val cMat = cStreamer.io.readData.bits.asTypeOf(Vec(8, Vec(8, SInt(32.W))))

  val dMat = Wire(Vec(8, Vec(8, SInt(32.W))))

  // Transpose B:
  val bMatT = Wire(Vec(8, Vec(8, SInt(32.W))))
  for (k <- 0 until 8) {
    for (n <- 0 until 8) {
      bMatT(n)(k) := bMat(k)(n);
    }
  }

  // Compute GeMM:
  for (n <- 0 until 8) {
    for (m <- 0 until 8) {
      val prod = (aMat(m) zip bMatT(n)).map { case (x, y) => (x * y).asSInt }
      val dot = prod.reduce(_ +& _)
      dMat(m)(n) := dot
    }
  }
  cStreamer.io.writeData.bits := dMat.asUInt

  csrItf.io.done := cStreamer.io.done

  def getConfig = TensorCoreConfig("tensorcore", 234)
}

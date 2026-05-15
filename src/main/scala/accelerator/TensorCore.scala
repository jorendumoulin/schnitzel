package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import csr.CsrIO
import csr.CsrInterface
import datapath.AluArray
import config.AcceleratorConfig

class TensorCore(addrWidth: Int, dataWidth: Int, M: Int = 4, N: Int = 4, K: Int = 4) extends Module {

  // Automatically determine port sizes based on array width and data width
  var aports = Seq(M)
  if (K > dataWidth / 8) aports = K / (dataWidth / 8) +: aports
  var bports = Seq(K)
  if (N > dataWidth / 8) bports = N / (dataWidth / 8) +: bports
  var cports = Seq(M)
  if (N > dataWidth / 32) cports = N / (dataWidth / 32) +: cports

  // CSR interface:
  class CsrVals extends Bundle {
    val aStreamerConfig = new AffineAguConfig(6, aports)
    val bStreamerConfig = new AffineAguConfig(6, bports)
    val cStreamerConfig = new AffineAguConfig(6, cports)
    def numRegs = aStreamerConfig.numRegs + bStreamerConfig.numRegs + cStreamerConfig.numRegs
  }
  val csrItf = Module(new CsrInterface((new CsrVals).numRegs, 0x900))
  val csrVals = VecInit(csrItf.io.vals.reverse).asTypeOf(new CsrVals)

  // IO definitions:
  val io = IO(new Bundle {
    val aData = Vec(csrVals.aStreamerConfig.numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val bData = Vec(csrVals.bStreamerConfig.numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val cData = Vec(csrVals.cStreamerConfig.numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val csr = Flipped(new CsrIO)
  })

  csrItf.io.csr <> io.csr

  val aStreamer = Module(new Streamer(csrVals.aStreamerConfig, 6, dataWidth));
  val bStreamer = Module(new Streamer(csrVals.bStreamerConfig, 6, dataWidth));
  val cStreamer = Module(new Streamer(csrVals.cStreamerConfig, 6, dataWidth));

  aStreamer.io.tcdmReqs <> io.aData
  aStreamer.io.config := csrVals.aStreamerConfig
  aStreamer.io.spatialDimMask := VecInit(Seq.fill(1)(true.B))
  aStreamer.io.start := csrItf.io.start
  aStreamer.io.writeData := DontCare
  aStreamer.io.dir := StreamerDir.read
  val aMat = aStreamer.io.readData.bits.asTypeOf(Vec(M, Vec(K, SInt(8.W))))

  bStreamer.io.tcdmReqs <> io.bData
  bStreamer.io.config := csrVals.bStreamerConfig
  bStreamer.io.spatialDimMask := VecInit(Seq.fill(1)(true.B))
  bStreamer.io.start := csrItf.io.start
  bStreamer.io.writeData := DontCare
  bStreamer.io.dir := StreamerDir.read
  val bMat = bStreamer.io.readData.bits.asTypeOf(Vec(K, Vec(N, SInt(8.W))))

  cStreamer.io.tcdmReqs <> io.cData
  cStreamer.io.config := csrVals.cStreamerConfig
  cStreamer.io.spatialDimMask := VecInit(Seq.fill(2)(true.B))
  cStreamer.io.start := csrItf.io.start
  cStreamer.io.dir := StreamerDir.readWrite
  val cMat = cStreamer.io.readData.bits.asTypeOf(Vec(M, Vec(N, SInt(32.W))))

  // Produce output result:
  val dMat = Wire(Vec(M, Vec(N, SInt(32.W))))

  for (m <- 0 until M) {
    for (n <- 0 until N) {
      val dot = (0 until K)
        .map(k => aMat(m)(k) * bMat(k)(n))
        .reduce(_ +& _)
      dMat(m)(n) := dot + cMat(m)(n)
    }
  }
  cStreamer.io.writeData.bits := dMat.asUInt

  // Flow control
  val go =
    aStreamer.io.readData.valid && bStreamer.io.readData.valid && cStreamer.io.readData.valid && cStreamer.io.writeData.ready
  aStreamer.io.readData.ready := go
  bStreamer.io.readData.ready := go
  cStreamer.io.readData.ready := go
  cStreamer.io.writeData.valid := go

  csrItf.io.done := cStreamer.io.done

  def getConfig = AcceleratorConfig(
    "tensorcore",
    Map(
      "M" -> ujson.Num(M),
      "N" -> ujson.Num(N),
      "K" -> ujson.Num(K),
      "a" -> aStreamer.getConfig,
      "b" -> bStreamer.getConfig,
      "c" -> cStreamer.getConfig
    )
  )
}

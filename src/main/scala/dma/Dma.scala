package dma

import chisel3._
import axi.AXIConfig
import core.DecoupledBusIO
import axi.AXIBundle
import streamer.Streamer
import streamer.AffineAguConfig
import streamer.AffineAgu
import axi.DecoupledIOToAXI
import csr.CsrIO
import csr.CsrInterface
import streamer.StreamerDir

object DmaDir extends ChiselEnum { val readAxi, writeAxi = Value; }

// DMA instantiates streamer <-> AXI bus
class Dma(addrWidth: Int, dataWidth: Int, axiConfig: AXIConfig, id: Int) extends Module {

  val numPorts = axiConfig.dataWidth / dataWidth;

  // warning: using this to reinterpret the vec of values, results in the
  // opposite ordering of signals as they are presented here:
  // additionally, all signals here should be 32 bits.
  class CsrVals extends Bundle {
    val streamerConfig = new AffineAguConfig(4, Seq(2, 2, 2))
    val axiStreamerConfig = new AffineAguConfig(4, Seq())
    val dir = UInt(32.W)
  }

  val io = IO(new Bundle {
    val data = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth));
    val axi = new AXIBundle(axiConfig)
    val csr = Flipped(new CsrIO)
  })

  val csrItf = Module(new CsrInterface(12 + 9 + 1, 0x900))
  csrItf.io.csr <> io.csr
  val csrVals = VecInit(csrItf.io.vals.reverse).asTypeOf(new CsrVals)
  dontTouch(csrVals)
  val dir = csrVals.dir(0).asTypeOf(DmaDir())

  // Use streamer for tcdm requests
  val streamer = Module(new Streamer(4, Seq(2, 2, 2), 3, addrWidth, dataWidth));
  streamer.io.tcdmReqs <> io.data
  streamer.io.config := csrVals.streamerConfig
  streamer.io.start := csrItf.io.start

  // Use affine agu for AXI address generation
  val axiAgu = Module(new AffineAgu(4, Seq(), 2))
  axiAgu.io.config := csrVals.axiStreamerConfig;
  axiAgu.io.start := csrItf.io.start;

  val memToAxi = Module(new DecoupledIOToAXI(addrWidth, dataWidth, axiConfig, id));
  io.axi <> memToAxi.io.axi
  // streamer -> axi
  memToAxi.io.bus.req.bits.ben := 1.U.asTypeOf(memToAxi.io.bus.req.bits.ben)
  memToAxi.io.bus.req.bits.addr := axiAgu.io.addrs(0).bits
  memToAxi.io.bus.req.bits.wen := dir === DmaDir.writeAxi
  when(dir === DmaDir.writeAxi) { // writeAxi, readTcdm
    memToAxi.io.bus.req.bits.wen := true.B
    memToAxi.io.bus.req.valid := axiAgu.io.addrs(0).valid && streamer.io.read.valid
    memToAxi.io.bus.req.bits.wdata := streamer.io.read.bits
    axiAgu.io.addrs(0).ready := memToAxi.io.bus.req.ready
    streamer.io.read.ready := true.B;
  }.otherwise { // readAxi, writeTcdm
    memToAxi.io.bus.req.bits.wen := false.B
    memToAxi.io.bus.req.valid := axiAgu.io.addrs(0).valid
    memToAxi.io.bus.req.bits.wdata := DontCare
    axiAgu.io.addrs(0).ready := memToAxi.io.bus.req.ready
    streamer.io.read.ready := false.B;
    // streamer.io.read.ready := memToAxi.io.bus.req.fire
  }

  // axi -> streamer
  when(dir === DmaDir.writeAxi) {
    memToAxi.io.bus.rsp.ready := true.B;
    streamer.io.write.valid := false.B;
    streamer.io.write.bits := DontCare
    streamer.io.dir := StreamerDir.read
  }.otherwise {
    memToAxi.io.bus.rsp.ready := streamer.io.write.ready
    streamer.io.write.valid := memToAxi.io.bus.rsp.valid
    streamer.io.write.bits := memToAxi.io.bus.rsp.bits.data
    streamer.io.dir := StreamerDir.write
  }

  csrItf.io.done := axiAgu.io.done && streamer.io.done

}

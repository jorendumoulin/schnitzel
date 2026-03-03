package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import csr.CsrIO
import csr.CsrInterface
import datapath.AluArray
import chisel3.util.DecoupledIO
import accelerator.Accelerator
import dataclass.data

// Accelerator instantiates streamer <-> datapath <-> streamer
class AluAccelerator(addrWidth: Int, dataWidth: Int) extends Accelerator(addrWidth, dataWidth) {

  val temporalUnroll = 1
  val spatialUnroll = 4 // Hardcode spatial unrolling
  val numPorts = spatialUnroll

  // warning: using this to reinterpret the vec of values, results in the
  // opposite ordering of signals as they are presented here:
  // additionally, all signals here should be 32 bits.
  class AluExtraConfigs extends Bundle {
    val select = Input(UInt(32.W))
    val numRegs = 1
  }
  class CsrVals extends Bundle {
    val aStreamer = new AffineAguConfig(temporalUnroll, Seq(spatialUnroll))
    val bStreamer = new AffineAguConfig(temporalUnroll, Seq(spatialUnroll))
    val cStreamer = new AffineAguConfig(temporalUnroll, Seq(spatialUnroll))
    val extra = new AluExtraConfigs
    def numRegs =
      aStreamer.numRegs + bStreamer.numRegs + cStreamer.numRegs + extra.numRegs
  }

  val io = IO(new Bundle {
    val tcdm = new Bundle {
      val a = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth))
      val b = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth))
      val c = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth))
    }
    val csr = Flipped(new CsrIO)
  })

  val csrItf = Module(new CsrInterface((new CsrVals).numRegs, 0x900))
  csrItf.io.csr <> io.csr
  val csrStart = csrItf.io.start
  val csrVals = VecInit(csrItf.io.vals.reverse).asTypeOf(new CsrVals)
  dontTouch(csrVals)

  val aluArray = Module(new AluArray(spatialUnroll, dataWidth))
  val truncated_sel = csrVals.extra.select.asTypeOf(UInt(2.W))
  aluArray.io.sel := truncated_sel

  val queueDepth = 3
  // Use streamers for tcdm requests
  val aStreamer =
    setupStreamer(csrVals.aStreamer, StreamerDir.read, io.tcdm.a, aluArray.io.A_in, csrStart)
  val bStreamer =
    setupStreamer(csrVals.bStreamer, StreamerDir.read, io.tcdm.b, aluArray.io.B_in, csrStart)
  val cStreamer =
    setupStreamer(csrVals.cStreamer, StreamerDir.write, io.tcdm.c, aluArray.io.C_out, csrStart)
  csrItf.io.done := cStreamer.io.done
}

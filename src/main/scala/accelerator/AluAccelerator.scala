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

  val csrItf = Module(new CsrInterface((new CsrVals).numRegs, 0x900))
  csrItf.io.csr <> io.csr
  val csrStart = csrItf.io.start
  val csrVals = VecInit(csrItf.io.vals.reverse).asTypeOf(new CsrVals)
  dontTouch(csrVals)

  val aluArray = Module(new AluArray(parallelUnroll, dataWidth))
  val truncated_sel = csrVals.select.asTypeOf(UInt(2.W))
  aluArray.io.sel := truncated_sel

  val queueDepth = 3
  // Use streamers for tcdm requests
  val aStreamer =
    setupStreamer(csrVals.aStreamerConfig, StreamerDir.read, io.aData, aluArray.io.A_in, csrStart)
  val bStreamer =
    setupStreamer(csrVals.bStreamerConfig, StreamerDir.read, io.bData, aluArray.io.B_in, csrStart)
  val cStreamer =
    setupStreamer(csrVals.cStreamerConfig, StreamerDir.write, io.cData, aluArray.io.C_out, csrStart)
  csrItf.io.done := cStreamer.io.done
}

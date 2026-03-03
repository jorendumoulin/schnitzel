package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import csr.CsrIO
import csr.CsrInterface
import datapath.AluArray
import chisel3.util.DecoupledIO

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

  val csrItf = Module(new CsrInterface((new CsrVals).numRegs, 0x900))
  csrItf.io.csr <> io.csr
  val csrVals = VecInit(csrItf.io.vals.reverse).asTypeOf(new CsrVals)
  dontTouch(csrVals)

  // helper function to avoid repeating boilerplate
  def setupStreamer(config: AffineAguConfig, dir: StreamerDir.Type, target: DecoupledIO[Vec[UInt]]) = {
    val s = Module(Streamer(config.nTemporalDims, config.spatialDimSizes, 3, addrWidth, dataWidth))
    // All streamers take the same start signal
    s.io.start := csrItf.io.start
    // All streamers take their own config for CSR setup
    s.io.config := config
    s.io.dir := dir
    // Streamer --> Acc
    // If the streamer is a "read streamer", connect write to don't care
    if (dir == StreamerDir.read) {
      target.valid := s.io.read.valid
      s.io.read.ready := target.ready
      target.bits := s.io.read.bits.asTypeOf(target.bits)
      s.io.write := DontCare
    }
    // Acc --> Streamer
    // If the streamer is a "write streamer", connect read to don't care
    else {
      s.io.write.valid := target.valid
      target.ready := s.io.write.ready
      s.io.write.bits := target.bits.asTypeOf(s.io.write.bits)
      s.io.read := DontCare
    }

    s
  }

  val aluArray = Module(new AluArray(parallelUnroll, dataWidth))
  val truncated_sel = csrVals.select.asTypeOf(UInt(2.W))
  aluArray.io.sel := truncated_sel

  val queueDepth = 3
  // Use streamers for tcdm requests
  val aStreamer = setupStreamer(csrVals.aStreamerConfig, StreamerDir.read, aluArray.io.A_in)
  aStreamer.io.tcdmReqs <> io.aData

  val bStreamer = setupStreamer(csrVals.bStreamerConfig, StreamerDir.read, aluArray.io.B_in)
  bStreamer.io.tcdmReqs <> io.bData

  val cStreamer = setupStreamer(csrVals.cStreamerConfig, StreamerDir.write, aluArray.io.C_out)
  cStreamer.io.tcdmReqs <> io.cData

  csrItf.io.done := cStreamer.io.done
}

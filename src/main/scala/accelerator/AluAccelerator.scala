package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import csr.CsrIO
import csr.CsrInterface
import datapath.AluArray
import chisel3.util.DecoupledIO
import accelerator.{Accelerator, AcceleratorStreamer, AcceleratorConfig}
import dataclass.data

object AluAcceleratorConfig {
  // A helper to generate a "Standard" 4-lane ALU configuration
  def default(addrWidth: Int = 32, dataWidth: Int = 32): AcceleratorConfig = {
    val temporalUnroll = 1
    val spatialUnroll = 4
    val spatialDims = Seq(spatialUnroll)

    AcceleratorConfig(
      name = "DefaultAlu",
      addrWidth = addrWidth,
      dataWidth = dataWidth,
      extraParams = 1,
      streamers = Seq(
        AcceleratorStreamer("A", StreamerDir.read, new AffineAguConfig(temporalUnroll, spatialDims)),
        AcceleratorStreamer("B", StreamerDir.read, new AffineAguConfig(temporalUnroll, spatialDims)),
        AcceleratorStreamer("C", StreamerDir.write, new AffineAguConfig(temporalUnroll, spatialDims))
      )
    )
  }
}

class AluAccelerator(cfg: AcceleratorConfig = AluAcceleratorConfig.default()) extends Accelerator(cfg) {
  val spatialUnroll = 4
  val numPorts = spatialUnroll
  val aluArray = Module(new AluArray(spatialUnroll, cfg.dataWidth))
  override def datapathInputs: Seq[DecoupledIO[Vec[UInt]]] = Seq(aluArray.io.A_in, aluArray.io.B_in)
  override def datapathOutputs: Seq[DecoupledIO[Vec[UInt]]] = Seq(aluArray.io.C_out)
  aluArray.io.sel := extraCsrParams(0)(1, 0)
  val writeDoneSignals = streamers.collect { case (s, dir) if dir == StreamerDir.write => s.io.done }
  csrItf.io.done := writeDoneSignals.foldLeft(true.B)(_ && _)
}

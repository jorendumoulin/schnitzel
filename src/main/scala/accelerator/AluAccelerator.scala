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

  val spatialWidth = cfg.streamers.head.affineConfig.spatialDimSizes.product
  val aluArray = Module(new AluArray(spatialWidth, cfg.dataWidth))
  aluArray.io.A_in <> datapathInputs(0)
  aluArray.io.B_in <> datapathInputs(1)
  datapathOutputs(0) <> aluArray.io.C_out
  aluArray.io.sel := extraParams(0)(1, 0)
}

package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import chisel3.util.DecoupledIO
import chisel3.util.MixedVec
import csr.{CsrIO, CsrInterface}

case class AcceleratorStreamer(
    name: String,
    dir: StreamerDir.Type,
    affineConfig: AffineAguConfig
)

case class AcceleratorConfig(
    name: String,
    streamers: Seq[AcceleratorStreamer],
    extraParams: Int,
    dataWidth: Int,
    addrWidth: Int
)

abstract class Accelerator(cfg: AcceleratorConfig) extends Module {
  val io = IO(new Bundle {
    // Outputs to TCDM
    val tcdm = MixedVec(cfg.streamers.map { s =>
      Vec(s.affineConfig.spatialDimSizes.product, new DecoupledBusIO(cfg.addrWidth, cfg.dataWidth))
    })
    // to interface with Control and status registers
    val csr = Flipped(new CsrIO)
  })

  def datapathInputs: Seq[DecoupledIO[Vec[UInt]]]
  def datapathOutputs: Seq[DecoupledIO[Vec[UInt]]]

  val totalCsrRegs = cfg.streamers.map(s => s.affineConfig.numRegs).sum + cfg.extraParams
  val csrItf = Module(new CsrInterface(totalCsrRegs, 0x900))
  csrItf.io.csr <> io.csr

  private var regOffset = 0
  lazy val streamers = {
    var inIdx = 0
    var outIdx = 0
    cfg.streamers.zipWithIndex.map { case (accStreamer, i) =>
      // Extract this streamer's slice of CSR values
      val streamerCsr =
        VecInit(csrItf.io.vals.slice(regOffset, regOffset + accStreamer.affineConfig.numRegs).reverse)
          .asTypeOf(accStreamer.affineConfig)
      regOffset += accStreamer.affineConfig.numRegs
      val datapathPort = if (accStreamer.dir == StreamerDir.read) {
        val p = datapathInputs(inIdx)
        inIdx += 1
        p
      } else {
        val p = datapathOutputs(outIdx)
        outIdx += 1
        p
      }
      val s = setupStreamer(
        config = streamerCsr,
        dir = accStreamer.dir,
        tcdmSide = io.tcdm(i),
        accSide = datapathPort,
        start = csrItf.io.start
      )
      (s, accStreamer.dir)
    }

  }
  // After the streamers loop finishes, regOffset is at the start of the extra params
  lazy val extraCsrParams = {
    // We force the streamers to initialize first so regOffset is correct
    val _ = streamers

    // Slice from the current offset to the end
    val extraSlice = csrItf.io.vals.slice(regOffset, regOffset + cfg.extraParams)

    // Reverse it if you want to maintain the same ordering convention as the streamers
    VecInit(extraSlice.reverse)
  }

  def setupStreamer(
      config: AffineAguConfig,
      dir: StreamerDir.Type,
      tcdmSide: Vec[core.DecoupledBusIO],
      accSide: DecoupledIO[Vec[UInt]],
      start: Bool
  ) = {
    val s = Module(
      Streamer(config.nTemporalDims, config.spatialDimSizes, 3, cfg.addrWidth, cfg.dataWidth)
    )
    // All streamers take the same start signal
    s.io.tcdmReqs <> tcdmSide
    s.io.start := start
    // All streamers take their own config for CSR setup
    s.io.config := config
    s.io.dir := dir
    // Streamer --> Acc
    // If the streamer is a "read streamer", connect write to don't care
    if (dir == StreamerDir.read) {
      accSide.valid := s.io.read.valid
      s.io.read.ready := accSide.ready
      accSide.bits := s.io.read.bits.asTypeOf(accSide.bits)
      s.io.write := DontCare
    }
    // Acc --> Streamer
    // If the streamer is a "write streamer", connect read to don't care
    else {
      s.io.write.valid := accSide.valid
      accSide.ready := s.io.write.ready
      s.io.write.bits := accSide.bits.asTypeOf(s.io.write.bits)
      s.io.read := DontCare
    }

    s
  }
}

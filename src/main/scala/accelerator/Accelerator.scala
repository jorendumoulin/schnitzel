package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import chisel3.util.DecoupledIO

abstract class Accelerator(addrWidth: Int, dataWidth: Int) extends Module {
  def setupStreamer(
      config: AffineAguConfig,
      dir: StreamerDir.Type,
      tcdmSide: Vec[core.DecoupledBusIO],
      accSide: DecoupledIO[Vec[UInt]],
      start: Bool
  ) = {
    val s = Module(
      Streamer(config.nTemporalDims, config.spatialDimSizes, 3, addrWidth, dataWidth)
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

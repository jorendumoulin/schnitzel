package accelerator

import chisel3._
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import chisel3.util.{DecoupledIO, MixedVec, Decoupled}
import csr.{CsrIO, CsrInterface}
import scala.collection.mutable

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
    val tcdm = MixedVec(cfg.streamers.map { s =>
      Vec(s.affineConfig.spatialDimSizes.product, new DecoupledBusIO(cfg.addrWidth, cfg.dataWidth))
    })
    val csr = Flipped(new CsrIO)
  })

  // 1. CSR Setup
  val totalCsrRegs = cfg.streamers.map(_.affineConfig.numRegs).sum + cfg.extraParams
  val csrItf = Module(new CsrInterface(totalCsrRegs, 0x900))
  csrItf.io.csr <> io.csr
  private val csrValues = csrItf.io.vals.reverse

  // 2. CSR Slicing Logic
  private var offset = 0
  val streamerConfigs = cfg.streamers.map { s =>
    val slice = VecInit(csrValues.slice(offset, offset + s.affineConfig.numRegs)).asTypeOf(s.affineConfig)
    offset += s.affineConfig.numRegs
    slice
  }
  val extraParams = VecInit(csrValues.slice(offset, offset + cfg.extraParams))

  // 3. Streamer Instantiation & Bridging
  // These are the lists the Subclass will use to connect its Datapath
  val datapathInputs = mutable.ListBuffer[DecoupledIO[Vec[UInt]]]()
  val datapathOutputs = mutable.ListBuffer[DecoupledIO[Vec[UInt]]]()
  val writeDoneSignals = mutable.ListBuffer[Bool]()

  cfg.streamers.zipWithIndex.foreach { case (sCfg, i) =>
    val s = Module(
      new Streamer(
        sCfg.affineConfig.nTemporalDims,
        sCfg.affineConfig.spatialDimSizes,
        3,
        cfg.addrWidth,
        cfg.dataWidth
      )
    )

    s.io.tcdmReqs <> io.tcdm(i)
    s.io.config := streamerConfigs(i)
    s.io.dir := sCfg.dir
    s.io.start := csrItf.io.start

    val numLanes = sCfg.affineConfig.spatialDimSizes.product

    if (sCfg.dir == StreamerDir.read) {
      s.io.write := DontCare
      // Bridge: Streamer (UInt) -> Datapath (Vec[UInt])
      val bridge = Wire(Decoupled(Vec(numLanes, UInt(cfg.dataWidth.W))))
      bridge.valid := s.io.read.valid
      s.io.read.ready := bridge.ready
      bridge.bits := s.io.read.bits.asTypeOf(bridge.bits)
      datapathInputs += bridge
    } else {
      s.io.read := DontCare
      // Bridge: Datapath (Vec[UInt]) -> Streamer (UInt)
      val bridge = Wire(Flipped(Decoupled(Vec(numLanes, UInt(cfg.dataWidth.W)))))
      s.io.write.valid := bridge.valid
      bridge.ready := s.io.write.ready
      s.io.write.bits := bridge.bits.asUInt
      datapathOutputs += bridge
      writeDoneSignals += s.io.done
    }
  }

  csrItf.io.done := writeDoneSignals.toSeq.foldLeft(true.B)(_ && _)
}

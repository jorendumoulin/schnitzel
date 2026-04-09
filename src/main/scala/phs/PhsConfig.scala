package phs

import upickle.default.{ReadWriter => RW, macroRW}

// --- PHS Streamer Config ---

case class PhsStreamerConfig(
    streamType: String, // "read" or "write"
    nTemporalDims: Int,
    spatialDimSizes: Seq[Int]
) {
  def numTcdmPorts: Int = spatialDimSizes.product
  def numCsrRegs: Int = 1 + nTemporalDims * 2 + spatialDimSizes.length
}
object PhsStreamerConfig { implicit val rw: RW[PhsStreamerConfig] = macroRW }

// --- PHS Accelerator Config ---

case class PhsAcceleratorConfig(
    streamers: Seq[PhsStreamerConfig],
    numSwitches: Int,
    switchBitwidths: Seq[Int] = Seq(),
    moduleName: String = "",
    svPath: String = ""
) {
  def totalTcdmPorts: Int = streamers.map(_.numTcdmPorts).sum
  def numCsrRegs: Int = streamers.map(_.numCsrRegs).sum + numSwitches

  /** Get bitwidth for switch i. Falls back to 32 (full CSR width) if not specified. */
  def switchBitwidth(i: Int): Int =
    if (i < switchBitwidths.length) switchBitwidths(i) else 32

  def readStreamers: Seq[PhsStreamerConfig] = streamers.filter(_.streamType == "read")
  def writeStreamers: Seq[PhsStreamerConfig] = streamers.filter(_.streamType == "write")
}
object PhsAcceleratorConfig {
  implicit val rw: RW[PhsAcceleratorConfig] = macroRW

  /** Default config matching the existing ALU accelerator: 2 read + 1 write streamer, 1 switch */
  val defaultAlu = PhsAcceleratorConfig(
    streamers = Seq(
      PhsStreamerConfig("read", 1, Seq(4)),
      PhsStreamerConfig("read", 1, Seq(4)),
      PhsStreamerConfig("write", 1, Seq(4))
    ),
    numSwitches = 1,
    switchBitwidths = Seq(2),
    moduleName = "acc1_array",
    svPath = "src/main/resources/phs/acc1_array.sv"
  )
}

// --- PHS system config for config.json export ---

case class PhsMemoryConfig(name: String, start: Long, size: Long)
object PhsMemoryConfig { implicit val rw: RW[PhsMemoryConfig] = macroRW }

/** Accelerator entry in the PHS config. Uses a type discriminator so the
  * Python parser can create the right accelerator object. */
sealed trait PhsAccelEntry { def `type`: String }

case class PhsAccelPhsEntry(
    `type`: String,
    streamers: Seq[PhsStreamerConfig],
    numSwitches: Int,
    switchBitwidths: Seq[Int],
    moduleName: String,
    svPath: String
) extends PhsAccelEntry
object PhsAccelPhsEntry { implicit val rw: RW[PhsAccelPhsEntry] = macroRW }

case class PhsAccelDmaEntry(`type`: String) extends PhsAccelEntry
object PhsAccelDmaEntry { implicit val rw: RW[PhsAccelDmaEntry] = macroRW }

object PhsAccelEntry {
  implicit val rw: RW[PhsAccelEntry] = RW.merge(
    macroRW[PhsAccelPhsEntry],
    macroRW[PhsAccelDmaEntry]
  )
}

case class PhsCoreConfig(hart_id: Int, accelerators: List[PhsAccelEntry])
object PhsCoreConfig { implicit val rw: RW[PhsCoreConfig] = macroRW }

case class PhsClusterConfig(memory: PhsMemoryConfig, cores: List[PhsCoreConfig])
object PhsClusterConfig { implicit val rw: RW[PhsClusterConfig] = macroRW }

case class PhsSystemConfig(memory: PhsMemoryConfig, clusters: List[PhsClusterConfig])
object PhsSystemConfig { implicit val rw: RW[PhsSystemConfig] = macroRW }

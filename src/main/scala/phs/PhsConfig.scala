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

// --- PHS metadata for config.json export ---

case class PhsMemoryConfig(name: String, start: Long, size: Long)
object PhsMemoryConfig { implicit val rw: RW[PhsMemoryConfig] = macroRW }

case class PhsCoreConfig(hart_id: Int, accelerators: List[PhsAcceleratorConfig])
object PhsCoreConfig { implicit val rw: RW[PhsCoreConfig] = macroRW }

case class PhsClusterConfig(memory: PhsMemoryConfig, cores: List[PhsCoreConfig])
object PhsClusterConfig { implicit val rw: RW[PhsClusterConfig] = macroRW }

case class PhsSystemConfig(memory: PhsMemoryConfig, clusters: List[PhsClusterConfig])
object PhsSystemConfig { implicit val rw: RW[PhsSystemConfig] = macroRW }

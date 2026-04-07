package config
import upickle.default.{ReadWriter => RW, macroRW}

// --- Basic Components ---

case class MemoryConfig(name: String, start: Long, size: Long)
object MemoryConfig { implicit val rw: RW[MemoryConfig] = macroRW }

// --- PHS Accelerator Config ---

case class PhsStreamerConfig(
    streamType: String, // "read" or "write"
    nTemporalDims: Int,
    spatialDimSizes: Seq[Int]
) {
  def numTcdmPorts: Int = spatialDimSizes.product
  def numCsrRegs: Int = 1 + nTemporalDims * 2 + spatialDimSizes.length
}
object PhsStreamerConfig { implicit val rw: RW[PhsStreamerConfig] = macroRW }

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

// --- Accelerator Config Hierarchy ---

case class DmaConfig()
object DmaConfig { implicit val rw: RW[DmaConfig] = macroRW }

sealed trait Accelerator {}

case class PhsWrapper(`type`: String, config: PhsAcceleratorConfig) extends Accelerator
object PhsWrapper { implicit val rw: RW[PhsWrapper] = macroRW }

case class DmaWrapper(`type`: String, config: DmaConfig) extends Accelerator
object DmaWrapper { implicit val rw: RW[DmaWrapper] = macroRW }

// Keep AluWrapper for backwards compatibility with existing configs
case class AluConfig()
object AluConfig { implicit val rw: RW[AluConfig] = macroRW }
case class AluWrapper(`type`: String, config: AluConfig) extends Accelerator
object AluWrapper { implicit val rw: RW[AluWrapper] = macroRW }

object Accelerator {
  implicit val rw: RW[Accelerator] = RW.merge(
    macroRW[PhsWrapper],
    macroRW[DmaWrapper],
    macroRW[AluWrapper]
  )
}

case class CoreConfig(hart_id: Int, accelerators: List[Accelerator])
object CoreConfig { implicit val rw: RW[CoreConfig] = macroRW }

case class ClusterConfig(memory: MemoryConfig, cores: List[CoreConfig])
object ClusterConfig { implicit val rw: RW[ClusterConfig] = macroRW }

case class SystemConfig(memory: MemoryConfig, clusters: List[ClusterConfig])
object SystemConfig { implicit val rw: RW[SystemConfig] = macroRW }

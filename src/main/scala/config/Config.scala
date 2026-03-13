package config
import upickle.default.{ReadWriter => RW, macroRW}

// --- Basic Components ---

case class StreamerConfig(temporal_dims: Int, spatial_dims: List[Int])
object StreamerConfig { implicit val rw: RW[StreamerConfig] = macroRW }

case class MemoryConfig(name: String, start: Long, size: Long)
object MemoryConfig { implicit val rw: RW[MemoryConfig] = macroRW }

// --- Accelerator Config Hierarchy ---

sealed trait AcceleratorConfig
object AcceleratorConfig {
  implicit val rw: RW[AcceleratorConfig] = RW.merge(
    macroRW[DataMoverConfig.type],
    macroRW[SnaxAluConfig.type],
    macroRW[SnaxXdmaConfig.type],
    macroRW[GemmxConfig]
  )
}

case object DataMoverConfig extends AcceleratorConfig
case object SnaxAluConfig extends AcceleratorConfig
case object SnaxXdmaConfig extends AcceleratorConfig
case class GemmxConfig(m: Int, n: Int, k: Int, streamers: List[StreamerConfig]) extends AcceleratorConfig
object GemmxConfig { implicit val rw: RW[GemmxConfig] = macroRW }

// --- Wrapper Hierarchy (The Union Type) ---

sealed trait AcceleratorWrapper {
  def accelerator: AcceleratorConfig
}

object AcceleratorWrapper {
  implicit val rw: RW[AcceleratorWrapper] = RW.merge(
    macroRW[DataMoverWrapper.type],
    macroRW[SnaxAluWrapper.type],
    macroRW[SnaxXdmaWrapper.type],
    macroRW[GemmxWrapper]
  )
}

case object DataMoverWrapper extends AcceleratorWrapper {
  def accelerator = DataMoverConfig
}

case object SnaxAluWrapper extends AcceleratorWrapper {
  def accelerator = SnaxAluConfig
}

case object SnaxXdmaWrapper extends AcceleratorWrapper {
  def accelerator = SnaxXdmaConfig
}

case class GemmxWrapper(gemmx: GemmxConfig) extends AcceleratorWrapper {
  def accelerator = gemmx
}
object GemmxWrapper { implicit val rw: RW[GemmxWrapper] = macroRW }

// --- System Hierarchy ---

case class CoreConfig(accelerators: List[AcceleratorConfig])
object CoreConfig { implicit val rw: RW[CoreConfig] = macroRW }

case class ClusterConfig(memory: MemoryConfig, cores: List[CoreConfig])
object ClusterConfig { implicit val rw: RW[ClusterConfig] = macroRW }

case class SystemConfig(memory: MemoryConfig, clusters: List[ClusterConfig])
object SystemConfig { implicit val rw: RW[SystemConfig] = macroRW }

package config
import upickle.default.{ReadWriter => RW, macroRW}

// --- Basic Components ---

case class MemoryConfig(name: String, start: Long, size: Long)
object MemoryConfig { implicit val rw: RW[MemoryConfig] = macroRW }

case class AcceleratorConfig(
    `type`: String,
    params: Map[String, ujson.Value]
)
object AcceleratorConfig {
  implicit val rw: RW[AcceleratorConfig] = macroRW
}

case class CoreConfig(hart_id: Int, accelerators: List[AcceleratorConfig])
object CoreConfig { implicit val rw: RW[CoreConfig] = macroRW }

case class ClusterConfig(memory: MemoryConfig, cores: List[CoreConfig])
object ClusterConfig { implicit val rw: RW[ClusterConfig] = macroRW }

case class SystemConfig(memory: MemoryConfig, clusters: List[ClusterConfig])
object SystemConfig { implicit val rw: RW[SystemConfig] = macroRW }

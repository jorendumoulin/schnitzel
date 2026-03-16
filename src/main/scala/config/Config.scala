package config
import upickle.default.{ReadWriter => RW, macroRW}

// --- Basic Components ---

case class MemoryConfig(name: String, start: Long, size: Long)
object MemoryConfig { implicit val rw: RW[MemoryConfig] = macroRW }

// --- Accelerator Config Hierarchy ---
// Wrapper with type + config fields
sealed trait Accelerator {}

// Config is just a map of params
case class AluConfig(`type`: String, width: Int) extends Accelerator
object AluConfig { implicit val rw: RW[AluConfig] = macroRW }

case class DmaConfig(`type`: String) extends Accelerator
object DmaConfig { implicit val rw: RW[DmaConfig] = macroRW }

// case class AluWrapper(`type`: String, config: AluConfig) extends Accelerator
// object AluWrapper { implicit val rw: RW[AluWrapper] = macroRW }

// case class DmaWrapper(`type`: String, config: DmaConfig) extends Accelerator
// object DmaWrapper { implicit val rw: RW[DmaWrapper] = macroRW }

object Accelerator {
  implicit val rw: RW[Accelerator] = RW.merge(
    macroRW[AluConfig],
    macroRW[DmaConfig]
  )
}

case class CoreConfig(hart_id: Int, accelerators: List[Accelerator])
object CoreConfig { implicit val rw: RW[CoreConfig] = macroRW }

case class ClusterConfig(memory: MemoryConfig, cores: List[CoreConfig])
object ClusterConfig { implicit val rw: RW[ClusterConfig] = macroRW }

case class SystemConfig(memory: MemoryConfig, clusters: List[ClusterConfig])
object SystemConfig { implicit val rw: RW[SystemConfig] = macroRW }

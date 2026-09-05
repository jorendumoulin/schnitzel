package top

import chisel3._
import axi.{AXIBundle, AXIConfig, AXILiteBundle}
import cluster.Cluster
import config.{MemoryConfig, SystemConfig}

/** Single-clock PS/PL boundary. Width conversion and the PS live outside this top. externalMemory describes the
  * cluster-visible logical memory aperture, not the board's total physical DDR capacity. Address translation is not
  * implemented.
  */
class FPGATop(
    externalMemory: MemoryConfig = MemoryConfig("L3", 0L, 0x10000000L)
) extends RawModule {
  val aclk = IO(Input(Clock()))
  val aresetn = IO(Input(Bool()))
  val m_axi = IO(new AXIBundle(AXIConfig(idWidth = 6, dataWidth = 512)))
  val s_axi = IO(Flipped(new AXILiteBundle()))

  // Keep the complete integration interface, including currently unused metadata.
  dontTouch(m_axi)
  dontTouch(s_axi)

  val control = withClockAndReset(aclk, !aresetn) { Module(new FPGAControl) }
  val cluster = withClockAndReset(aclk, !aresetn || !control.io.run) {
    Module(new Cluster)
  }
  control.io.axi <> s_axi
  control.io.csr <> cluster.io.csr
  m_axi <> cluster.io.axi
  control.io.axiError :=
    (m_axi.b.fire && m_axi.b.bits.resp(1)) ||
      (m_axi.r.fire && m_axi.r.bits.resp(1))

  def getConfig: SystemConfig = SystemConfig(externalMemory, List(cluster.getConfig))
}

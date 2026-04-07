package top

import chisel3._

import cluster.{Cluster, PhsCluster}
import config.PhsAcceleratorConfig

/** Top-level with PHS accelerators.
  *
  * @param phsConfigs
  *   Per-core list of PHS accelerator configs (length 2). See [[PhsCluster]].
  */
class PhsTop(
    phsConfigs: Seq[Seq[PhsAcceleratorConfig]] = Seq(Seq(), Seq(PhsAcceleratorConfig.defaultAlu))
) extends Top {

  // Use "Top" as the module name so TopWrapper.sv works for both Top and PhsTop
  override def desiredName: String = "Top"

  override protected def makeCluster(): Cluster = Module(new PhsCluster(phsConfigs))
}

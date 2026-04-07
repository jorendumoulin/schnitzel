package cluster

import chisel3._

import core.CoreConfig
import accelerator.PhsAccelerator
import config.PhsAcceleratorConfig

/** Cluster with PHS accelerators instead of the default AluAccelerator.
  *
  * @param phsConfigs
  *   Per-core list of PHS accelerator configs. phsConfigs(0) = core 0, phsConfigs(1) = core 1. Core 0 always also has
  *   DMA.
  */
class PhsCluster(phsConfigs: Seq[Seq[PhsAcceleratorConfig]]) extends Cluster {

  override protected def makeAccelerators(): Seq[Seq[AcceleratorHandle]] = {
    // PHS accels start at 0x920 on core 0 (to avoid DMA's CSR range at 0x900-0x917)
    // and at 0x900 on core 1
    val baseAddrs = Seq(0x920L, 0x900L)

    phsConfigs.zipWithIndex.map { case (coreConfigs, coreIdx) =>
      coreConfigs.zipWithIndex.map { case (cfg, accelIdx) =>
        val acc = Module(new PhsAccelerator(CoreConfig.addrWidth, tcdmDataWidth, cfg))
        new AcceleratorHandle(
          tcdmPorts = acc.io.tcdmPorts.toSeq,
          csrPort = acc.io.csr,
          csrRange = (baseAddrs(coreIdx) + accelIdx * 0x20L, 0x20L),
          accelConfig = acc.getConfig
        )
      }
    }
  }
}

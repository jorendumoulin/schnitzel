package phs

import chisel3._

import core.DecoupledBusIO
import axi.AXIConfig
import axi.AxiToMem
import config.{SystemConfig, MemoryConfig}

/** Self-contained PHS top-level module.
  *
  * Same structure as the base Top, but instantiates PhsCluster with PHS accelerators instead of the default Cluster
  * with AluAccelerator.
  *
  * Unlike Top, there is no CVA6 manager core: the cluster runs standalone. The narrow memory port is kept (tied off) so
  * the shared sim/rtl/TopWrapper.sv still binds, and the cluster's global-barrier CSR is terminated locally.
  *
  * @param phsConfigs
  *   Per-core list of PHS accelerator configs (length 2). See [[PhsCluster]].
  */
class PhsTop(
    phsConfigs: Seq[Seq[PhsAcceleratorConfig]] = Seq(Seq(), Seq(PhsAcceleratorConfig.defaultAlu))
) extends Module {

  // Use "Top" as the module name so TopWrapper.sv works for both Top and PhsTop
  override def desiredName: String = "Top"

  val io = IO(new Bundle {
    val mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 512)
    // Unused without a manager core, but kept so TopWrapper.sv's port list matches.
    val narrow_mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 64)
  })

  val cluster = Module(new PhsCluster(phsConfigs))
  val toMem = Module(new AxiToMem(addrWidth = 32, dataWidth = 512, axiConfig = AXIConfig(dataWidth = 512, idWidth = 6)))
  toMem.io.axi <> cluster.io.axi
  io.mem <> toMem.io.mem

  // No manager: never issue narrow requests, never accept narrow responses.
  io.narrow_mem.req.valid := false.B
  io.narrow_mem.req.bits := DontCare
  io.narrow_mem.rsp.ready := true.B

  // No manager to synchronize with, so the global barrier (CSR 0x800) completes
  // immediately: every cluster request is accepted and reads return 0.
  cluster.io.csr.req.ready := true.B
  cluster.io.csr.rsp.rdata := 0.U

  def getConfig: SystemConfig = SystemConfig(
    MemoryConfig("L3", 0x2_0000_0000L, 0x2_0000_0000L),
    List(cluster.getConfig)
  )
}

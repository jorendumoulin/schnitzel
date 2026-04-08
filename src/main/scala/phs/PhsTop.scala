package phs

import chisel3._

import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIConfig, AXIDemux}
import core.CVA6
import axi.AxiToMem
import top.GlobalBarrier

/** Self-contained PHS top-level module.
  *
  * Same structure as the base Top, but instantiates PhsCluster with PHS accelerators instead of the default Cluster
  * with AluAccelerator.
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
    val narrow_mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 64)
  })

  val cluster = Module(new PhsCluster(phsConfigs))
  val toMem = Module(new AxiToMem(addrWidth = 32, dataWidth = 512, axiConfig = AXIConfig(dataWidth = 512, idWidth = 6)))
  toMem.io.axi <> cluster.io.axi
  io.mem <> toMem.io.mem

  val manager = Module(new CVA6)
  val managerToMem = Module(new AxiToMem(addrWidth = 32, dataWidth = 64, axiConfig = AXIConfig(dataWidth = 64)))
  val managerDemux = Module(new AXIDemux(AXIConfig(dataWidth = 64), 2, Seq((0x3000L, 0x4000L))))
  managerDemux.io.in <> manager.io.axi
  managerToMem.io.axi <> managerDemux.io.outs(1)
  io.narrow_mem <> managerToMem.io.mem

  val barrier = Module(new GlobalBarrier(AXIConfig(dataWidth = 64)))
  barrier.io.csr <> cluster.io.csr
  barrier.io.axi <> managerDemux.io.outs(0)

  def getConfig: PhsSystemConfig = PhsSystemConfig(
    PhsMemoryConfig("L3", 0x2_0000_0000L, 0x2_0000_0000L),
    List(cluster.getConfig)
  )
}

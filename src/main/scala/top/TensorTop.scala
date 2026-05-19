package top

import chisel3._

import core.{CVA6, DecoupledBusIO}
import axi.{AxiToMem, AXIDemux}
import cluster.TensorCluster
import config.{SystemConfig, MemoryConfig}

class TensorTop extends Module {

  override def desiredName = "Top"

  val io = IO(new Bundle {
    val mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 512)
    val narrow_mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 64)
  })

  val cluster = Module(new TensorCluster())
  AxiToMem(cluster.io.axi, io.mem)

  val manager = Module(new CVA6)
  val managerDemux = AXIDemux(manager.io.axi, Seq((0x3000L, 0x4000L)))
  AxiToMem(managerDemux.io.outs(1), io.narrow_mem)
  GlobalBarrier(cluster.io.csr, managerDemux.io.outs(0))

  def getConfig: SystemConfig = SystemConfig(
    MemoryConfig("L3", 0x2_0000_0000L, 0x2_0000_0000L),
    List(cluster.getConfig)
  )
}

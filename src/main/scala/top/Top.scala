package top

import chisel3._

import core.Core
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig, AXIDemux}
import cluster.Cluster
import core.CVA6
import axi.AxiToMem

class Top extends Module {

  val io = IO(new Bundle {
    val mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 512)
    val narrow_mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 64)
  })

  val cluster = Module(new Cluster())
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

}

package top

import chisel3._

import core.Core
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig}
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
  managerToMem.io.axi <> manager.io.axi
  io.narrow_mem <> managerToMem.io.mem

}

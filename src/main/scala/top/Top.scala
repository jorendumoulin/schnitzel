package top

import chisel3._

import core.Core
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig}
import cluster.Cluster
import core.BigCore
import core.CVA6
import axi.AxiToMem

class Top extends Module {

  val io = IO(new Bundle {
    val mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 512)
    val narrow_mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 64)
    // val axi = new AXIBundle(AXIConfig(dataWidth = 512))
    // val narrow_axi = new AXIBundle(AXIConfig(dataWidth = 64))
    // val mmio_axi = new AXIBundle(AXIConfig(addrWidth = 31, dataWidth = 64))
  })

  val cluster = Module(new Cluster())
  val toMem = Module(new AxiToMem(addrWidth = 32, dataWidth = 512, axiConfig = AXIConfig(dataWidth = 512)))
  toMem.io.axi <> cluster.io.axi
  io.mem <> toMem.io.mem

  // val manager = Module(new BigCore)
  // io.narrow_axi <> manager.io.axi
  // io.mmio_axi <> manager.io.mmio_axi

  val manager = Module(new CVA6)
  val managerToMem = Module(new AxiToMem(addrWidth = 32, dataWidth = 64, axiConfig = AXIConfig(dataWidth = 64)))
  managerToMem.io.axi <> manager.io.axi
  io.narrow_mem <> managerToMem.io.mem

}

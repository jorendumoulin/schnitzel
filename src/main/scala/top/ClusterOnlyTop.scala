package top

import chisel3._

import core.Core
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig}
import cluster.Cluster
import axi.AxiToMem

class ClusterOnlyTop extends Module {

  val io = IO(new Bundle {
    val mem = new DecoupledBusIO(addrWidth = 32, dataWidth = 512)
  })

  val cluster = Module(new Cluster())
  val toMem = Module(new AxiToMem(addrWidth = 32, dataWidth = 512, axiConfig = AXIConfig(dataWidth = 512)))
  toMem.io.axi <> cluster.io.axi
  io.mem <> toMem.io.mem
}

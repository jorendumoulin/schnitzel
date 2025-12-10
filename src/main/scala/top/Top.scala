package top

import chisel3._

import core.Core
import icache.ICache
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig}
import cluster.Cluster

class Top extends Module {

  val io = IO(new Bundle {
    val axi = new AXIBundle(AXIConfig(dataWidth = 512))
  })

  val cluster = Module(new Cluster())
  io.axi <> cluster.io.axi

}

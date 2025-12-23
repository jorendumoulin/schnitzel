package top

import chisel3._

import core.Core
import core.{DecoupledBusIO, CoreConfig}
import axi.{AXIBundle, AXIConfig}
import cluster.Cluster
import core.BigCore

class Top extends Module {

  val io = IO(new Bundle {
    val axi = new AXIBundle(AXIConfig(dataWidth = 512))
    val narrow_axi = new AXIBundle(AXIConfig(dataWidth = 64))
  })

  val cluster = Module(new Cluster())
  io.axi <> cluster.io.axi

  val manager = Module(new BigCore)
  io.narrow_axi <> manager.io.axi

}

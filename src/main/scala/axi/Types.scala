package axi

import chisel3._
import chisel3.util._

case class AXIConfig(
    idWidth: Int = 4,
    addrWidth: Int = 32,
    dataWidth: Int = 64,
    userWidth: Int = 1,
    lenWidth: Int = 8,
    sizeWidth: Int = 3,
    burstWidth: Int = 2,
    cacheWidth: Int = 4,
    protWidth: Int = 3,
    qosWidth: Int = 4,
    regionWidth: Int = 4,
    respWidth: Int = 2
) {
  def strbWidth: Int = dataWidth / 8
}

class AChan(cfg: AXIConfig = AXIConfig()) extends Bundle {
  val id = UInt(cfg.idWidth.W)
  val addr = UInt(cfg.addrWidth.W)
  val len = UInt(cfg.lenWidth.W)
  val size = UInt(cfg.sizeWidth.W)
  val burst = UInt(cfg.burstWidth.W)
  val lock = Bool()
  val cache = UInt(cfg.cacheWidth.W)
  val prot = UInt(cfg.protWidth.W)
  val qos = UInt(cfg.qosWidth.W)
  val region = UInt(cfg.regionWidth.W)
  val user = UInt(cfg.userWidth.W)

  def bytesPerBeat: UInt = (1.U << size)

}

class AWChan(cfg: AXIConfig) extends AChan(cfg)

class WChan(cfg: AXIConfig) extends Bundle {
  val data = UInt(cfg.dataWidth.W)
  val strb = UInt(cfg.strbWidth.W)
  val last = Bool()
  val user = UInt(cfg.userWidth.W)
}

class BChan(cfg: AXIConfig) extends Bundle {
  val id = UInt(cfg.idWidth.W)
  val resp = UInt(cfg.respWidth.W)
  val user = UInt(cfg.userWidth.W)
}

class ARChan(cfg: AXIConfig) extends AChan(cfg)

class RChan(cfg: AXIConfig) extends Bundle {
  val id = UInt(cfg.idWidth.W)
  val data = UInt(cfg.dataWidth.W)
  val resp = UInt(cfg.respWidth.W)
  val last = Bool()
  val user = UInt(cfg.userWidth.W)
}

class AXIBundle(cfg: AXIConfig) extends Bundle {
  // write:
  val aw = DecoupledIO(new AWChan(cfg))
  val w = DecoupledIO(new WChan(cfg))
  val b = Flipped(DecoupledIO(new BChan(cfg)))
  // read
  val ar = DecoupledIO(new ARChan(cfg))
  val r = Flipped(DecoupledIO(new RChan(cfg)))
}

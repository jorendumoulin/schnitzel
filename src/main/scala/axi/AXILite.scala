package axi

import chisel3._
import chisel3.util.Decoupled

class AXILiteAddress(addrWidth: Int) extends Bundle {
  val addr = UInt(addrWidth.W)
  val prot = UInt(3.W)
}

class AXILiteWriteData(dataWidth: Int) extends Bundle {
  val data = UInt(dataWidth.W)
  val strb = UInt((dataWidth / 8).W)
}

class AXILiteReadData(dataWidth: Int) extends Bundle {
  val data = UInt(dataWidth.W)
  val resp = UInt(2.W)
}

/** Master-oriented AXI-Lite interface; flip it for a register peripheral. */
class AXILiteBundle(addrWidth: Int = 12, dataWidth: Int = 32) extends Bundle {
  require(dataWidth == 32 || dataWidth == 64)
  val aw = Decoupled(new AXILiteAddress(addrWidth))
  val w = Decoupled(new AXILiteWriteData(dataWidth))
  val b = Flipped(Decoupled(UInt(2.W)))
  val ar = Decoupled(new AXILiteAddress(addrWidth))
  val r = Flipped(Decoupled(new AXILiteReadData(dataWidth)))
}

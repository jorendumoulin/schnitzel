package csr

import chisel3._
import chisel3.util.{MuxLookup, log2Ceil}
import csr.CsrIO

class CsrDemux(addrMap: Seq[(Long, Long)]) extends Module {

  require(addrMap.nonEmpty, "addrMap must have at least one entry")

  val numOuts = addrMap.length

  val io = IO(new Bundle {
    val in = Flipped(new CsrIO);
    val outs = Vec(numOuts, new CsrIO);
  })

  val idxBits = log2Ceil(numOuts)

  def decode(addr: UInt): UInt =
    addrMap.zipWithIndex.foldRight(0.U(idxBits.W)) { case ((entry, i), otherwise) =>
      val (base, size) = entry
      Mux(addr >= base.U && addr < (base + size).U, i.U(idxBits.W), otherwise)
    }

  def getBase(idx: UInt): UInt =
    addrMap.zipWithIndex.foldRight(0.U(12.W)) { case ((entry, i), otherwise) =>
      val (base, size) = entry
      Mux(idx === i.U, base.U, otherwise)
    }

  io.outs.foreach { out =>
    out.req.valid := false.B
    out.req.bits.addr := DontCare
    out.req.bits.wdata := DontCare
    out.req.bits.op := DontCare
  }

  val outSel = decode(io.in.req.bits.addr)
  val baseAddr = getBase(outSel)

  io.outs(outSel).req.valid := io.in.req.valid
  io.outs(outSel).req.bits.addr := io.in.req.bits.addr - baseAddr
  io.outs(outSel).req.bits.wdata := io.in.req.bits.wdata
  io.outs(outSel).req.bits.op := io.in.req.bits.op
  io.in.req.ready := io.outs(outSel).req.ready

  val rspMux = VecInit(io.outs.map(_.rsp.rdata))
  io.in.rsp.rdata := rspMux(outSel)
}

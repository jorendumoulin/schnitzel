package interconnect

import chisel3._
import core.DecoupledBusIO
import chisel3.util.log2Up
import chisel3.util.RRArbiter
import core.BusReq

class Interconnect(
    numInp: Int,
    numOut: Int,
    addrWidth: Int,
    dataWidth: Int
) extends Module {

  val io = IO(new Bundle {
    val ins = Vec(numInp, Flipped(new DecoupledBusIO(addrWidth, dataWidth)))
    val outs = Vec(numOut, new DecoupledBusIO(addrWidth, dataWidth))
  })

  // Bank selection
  // Address construction:
  // [bank addr | bank offset | byte offset]
  val byteOffsetWidth = log2Up(dataWidth / 8)
  val bankSelectWidth = log2Up(numOut)
  val bankSelect = VecInit(io.ins.map { in =>
    in.req.bits.addr(bankSelectWidth + byteOffsetWidth - 1, byteOffsetWidth)
  })

  // === Forward Request Routing (tcdm -> bank) ===
  val arbiters = Seq.fill(numOut)(Module(new RRArbiter(new BusReq(addrWidth, dataWidth), numInp)))

  // Connect relevant ready signal based on bank selection
  io.ins.zipWithIndex.foreach { case (io_in, i) =>
    io_in.req.ready := VecInit(arbiters.map(_.io.in(i).ready))(bankSelect(i))
  }

  arbiters.zipWithIndex.foreach { case (arbiter, out) =>
    // Connect the input bits to the arbiters.
    arbiter.io.in.zip(io.ins).foreach { case (in, io_in) => in.bits <> io_in.req.bits }
    // Only valid when the bank selection matches
    arbiter.io.in.zip(bankSelect).zip(io.ins).foreach { case ((in, bank), io_in) =>
      in.valid := io_in.req.valid && (bank === out.U)
    }
    // Connect to the memory output ports.
    arbiter.io.out <> io.outs(out).req
  }

  // === Response Routing ===

  // response arbitration is a simple mux based on bank selection in previous cycle
  // this assumes that the memory banks have a fixed 1-cycle latency
  val prevBankSelect = RegNext(bankSelect)
  val prevReqFire = RegNext(VecInit(io.ins.map(_.req.fire)))

  for (in <- 0 until numInp) {
    val bank = prevBankSelect(in)
    // bits
    io.ins(in).rsp.bits := io.outs(bank).rsp.bits
    // valid
    io.ins(in).rsp.valid := prevReqFire(in) && io.outs(bank).rsp.valid
    // ready
    when(prevReqFire(in)) {
      io.outs(bank).rsp.ready := io.ins(in).rsp.ready
    }.otherwise {
      io.outs(bank).rsp.ready := false.B
    }
  }

  // We should always be ready for bank response
  io.outs.foreach(_.rsp.ready := true.B)

}

package axi

import chisel3._
import chisel3.util.{Cat, Queue, RRArbiter, log2Up}

// Convenience constructor: derives outCfg by widening inCfg's idWidth by log2Ceil(numIns).
object AXIMux {
  def apply(cfg: AXIConfig, numIns: Int, maxWTrans: Int = 8): AXIMux =
    new AXIMux(cfg, cfg.copy(idWidth = cfg.idWidth + log2Up(numIns)), numIns, maxWTrans)
}

// AXI Multiplexer: numIns master ports -> one slave port.
//
// AR/AW: the winning master port index is prepended to the transaction ID before forwarding
// to the slave, making every in-flight ID globally unique across all masters.  This allows
// the slave (and any downstream crossbar) to reorder responses freely.
//
// R/B: the prepended upper bits of the returned ID select which master port to route the
// response back to; those bits are stripped before presenting the original ID to the master.
// No FIFO is required for R or B routing.
//
// W: the W channel carries no ID, so a FIFO still records the AW arbitration result and
// gates the AW channel when full.
//
// inCfg  -- AXIConfig for the ins ports (master-facing, narrower ID)
// outCfg -- AXIConfig for the out port  (slave-facing,  wider ID)
//           outCfg.idWidth must equal inCfg.idWidth + log2Ceil(numIns)
class AXIMux(inCfg: AXIConfig, outCfg: AXIConfig, numIns: Int, maxWTrans: Int = 8) extends Module {

  require(numIns >= 1, "numIns must be at least 1")
  require(maxWTrans >= 1, "maxWTrans must be at least 1")
  require(
    outCfg.idWidth == inCfg.idWidth + log2Up(numIns),
    s"outCfg.idWidth (${outCfg.idWidth}) must equal inCfg.idWidth (${inCfg.idWidth}) + log2Ceil(numIns) (${log2Up(numIns)})"
  )

  val io = IO(new Bundle {
    val ins = Vec(numIns, Flipped(new AXIBundle(inCfg)));
    val out = new AXIBundle(outCfg);
  })

  val idxBits = log2Up(numIns)

  // AR channel
  val arArb = Module(new RRArbiter(new ARChan(inCfg), numIns))
  arArb.io.in <> io.ins.map(_.ar)
  io.out.ar <> arArb.io.out
  // prepend master index to id:
  io.out.ar.bits.id := Cat(arArb.io.chosen, arArb.io.out.bits.id)

  // R channel: upper ID bits select the master port; strip them before returning
  val rSel = io.out.r.bits.id(outCfg.idWidth - 1, inCfg.idWidth)

  io.out.r.ready := false.B
  for (i <- 0 until numIns) {
    io.ins(i).r.valid := false.B
    io.ins(i).r.bits := io.out.r.bits
    io.ins(i).r.bits.id := io.out.r.bits.id(inCfg.idWidth - 1, 0)
  }
  when(io.out.r.valid) {
    io.ins(rSel).r.valid := true.B
    io.out.r.ready := io.ins(rSel).r.ready
  }

  // AW channel:
  // wFifo: records the AW arbitration winner; W data is routed from that port
  // popped on the last w beat.
  val wFifo = Module(new Queue(UInt(idxBits.W), maxWTrans))
  val awArb = Module(new RRArbiter(new AWChan(inCfg), numIns))
  awArb.io.in <> io.ins.map(_.aw)

  io.out.aw.valid := awArb.io.out.valid && wFifo.io.enq.ready
  io.out.aw.bits := awArb.io.out.bits
  io.out.aw.bits.id := Cat(awArb.io.chosen, awArb.io.out.bits.id)
  awArb.io.out.ready := io.out.aw.ready && wFifo.io.enq.ready

  wFifo.io.enq.valid := awArb.io.out.fire
  wFifo.io.enq.bits := awArb.io.chosen

  // W channel: steer write data from the master recorded at the W FIFO head
  val wSel = wFifo.io.deq.bits

  val awWins = awArb.io.out.valid && wFifo.io.enq.ready
  val awWinner = awArb.io.chosen
  val awWinnerHasW = io.ins(awWinner).w.valid

  wFifo.io.deq.ready := false.B
  io.out.w.valid := false.B
  io.out.w.bits := io.ins(0).w.bits
  for (i <- 0 until numIns) {
    io.ins(i).w.ready := false.B
  }
  when(awWins && awWinnerHasW) {
    io.out.w.valid := io.ins(awWinner).w.valid
    io.out.w.bits := io.ins(awWinner).w.bits
    io.ins(awWinner).w.ready := io.out.w.ready
    wFifo.io.deq.ready := io.out.w.fire && io.out.w.bits.last
  }.elsewhen(wFifo.io.deq.valid && !awWins) {
    io.out.w.valid := io.ins(wSel).w.valid
    io.out.w.bits := io.ins(wSel).w.bits
    io.ins(wSel).w.ready := io.out.w.ready
    wFifo.io.deq.ready := io.out.w.fire && io.out.w.bits.last
  }

  // B channel: upper ID bits select the master port; strip them before returning
  val bSel = io.out.b.bits.id(outCfg.idWidth - 1, inCfg.idWidth)

  io.out.b.ready := false.B
  for (i <- 0 until numIns) {
    io.ins(i).b.valid := false.B
    io.ins(i).b.bits := io.out.b.bits
    io.ins(i).b.bits.id := io.out.b.bits.id(inCfg.idWidth - 1, 0)
  }
  when(io.out.b.valid) {
    io.ins(bSel).b.valid := true.B
    io.out.b.ready := io.ins(bSel).b.ready
  }

}

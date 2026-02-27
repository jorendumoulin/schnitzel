package axi

import chisel3._
import chisel3.util.{Cat, Queue, RRArbiter, log2Up}

// Convenience constructor: derives outCfg by widening inCfg's idWidth by log2Ceil(numIns).
object AXIMux {
  def apply(cfg: AXIConfig, numIns: Int, maxWTrans: Int = 8): AXIMux =
    new AXIMux(cfg, cfg.copy(idWidth = cfg.idWidth + log2Up(numIns)), numIns, maxWTrans)
}

// AXI Multiplexer: connects numIns master ports to one slave port.
//
// AR/AW channels: round-robin arbitration selects a master; the master index is prepended
// to the transaction ID before forwarding to the slave, making every in-flight ID globally
// unique across all masters. This allows the slave (and any downstream crossbar) to reorder
// responses freely.
//
// R/B channels: the upper ID bits identify which master originated the transaction; those
// bits are stripped before presenting the original ID back to the master. No FIFO needed.
//
// W channel: carries no ID, so a FIFO records AW arbitration winners and gates AW when full.
// W data is routed based on the FIFO head (the pending AW winner).
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

  // AR channel: round-robin arbitration between masters, prepend master index to ID
  val arArb = Module(new RRArbiter(new ARChan(inCfg), numIns))
  arArb.io.in <> io.ins.map(_.ar)
  io.out.ar <> arArb.io.out
  io.out.ar.bits.id := Cat(arArb.io.chosen, arArb.io.out.bits.id)

  // R channel: route response back to original master using upper ID bits (no FIFO needed)
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

  // AW channel: arbitrate and record winner in FIFO; W data follows via FIFO
  // The FIFO stores which master won AW arbitration; W beats are drained in order.
  val wFifo = Module(new Queue(UInt(idxBits.W), maxWTrans))
  val awArb = Module(new RRArbiter(new AWChan(inCfg), numIns))
  awArb.io.in <> io.ins.map(_.aw)

  // Only assert AW when both arbiter has a winner AND FIFO has space
  io.out.aw.valid := awArb.io.out.valid && wFifo.io.enq.ready
  io.out.aw.bits := awArb.io.out.bits
  io.out.aw.bits.id := Cat(awArb.io.chosen, awArb.io.out.bits.id)
  awArb.io.out.ready := io.out.aw.ready && wFifo.io.enq.ready

  // Record AW winner in FIFO when AW fires
  wFifo.io.enq.valid := awArb.io.out.fire
  wFifo.io.enq.bits := awArb.io.chosen

  // W channel: steer data from the master recorded at FIFO head
  // Two cases: (1) new AW winner has W data ready, or (2) draining pending W from FIFO
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
  // Priority: new AW winner with W data > draining pending W from FIFO
  when(awWins && awWinnerHasW) {
    io.out.w.valid := io.ins(awWinner).w.valid
    io.out.w.bits := io.ins(awWinner).w.bits
    io.ins(awWinner).w.ready := io.out.w.ready
    // Pop FIFO on last beat of write transaction
    wFifo.io.deq.ready := io.out.w.fire && io.out.w.bits.last
  }.elsewhen(wFifo.io.deq.valid && !awWins) {
    io.out.w.valid := io.ins(wSel).w.valid
    io.out.w.bits := io.ins(wSel).w.bits
    io.ins(wSel).w.ready := io.out.w.ready
    wFifo.io.deq.ready := io.out.w.fire && io.out.w.bits.last
  }

  // B channel: route response back to original master using upper ID bits (no FIFO needed)
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

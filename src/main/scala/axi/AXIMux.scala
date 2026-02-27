package axi

import chisel3._
import chisel3.util.{Cat, RRArbiter, log2Up}

// Convenience constructor: derives outCfg by widening inCfg's idWidth by log2Ceil(numIns).
object AXIMux {
  def apply(cfg: AXIConfig, numIns: Int): AXIMux =
    new AXIMux(cfg, cfg.copy(idWidth = cfg.idWidth + log2Up(numIns)), numIns)
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
// W channel: only one in-flight write is allowed at a time. AW is gated while a write is
// pending; the pending flag is cleared when W's last beat completes.
//
// inCfg  -- AXIConfig for the ins ports (master-facing, narrower ID)
// outCfg -- AXIConfig for the out port  (slave-facing,  wider ID)
//           outCfg.idWidth must equal inCfg.idWidth + log2Ceil(numIns)
class AXIMux(inCfg: AXIConfig, outCfg: AXIConfig, numIns: Int) extends Module {

  require(numIns >= 1, "numIns must be at least 1")
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

  // W channel: gates AW when a write is in-flight; cleared on W last beat
  // (no FIFO needed since only one pending write is allowed)
  val wPending = RegInit(false.B)
  val wPendingMaster = RegInit(0.U(idxBits.W))

  // AW channel: round-robin arbitration, but blocked if write is pending
  val awArb = Module(new RRArbiter(new AWChan(inCfg), numIns))
  awArb.io.in <> io.ins.map(_.aw)
  io.out.aw <> awArb.io.out
  io.out.aw.bits.id := Cat(awArb.io.chosen, awArb.io.out.bits.id)

  // Block when write is happening:
  when(io.out.aw.fire) {
    wPending := true.B
    wPendingMaster := awArb.io.chosen
  }
  io.out.aw.valid := awArb.io.out.valid && !wPending
  awArb.io.out.ready := io.out.aw.ready && !wPending

  // W channel: steer data from the pending master
  val currentMaster = Mux(wPending, wPendingMaster, awArb.io.chosen)
  for (i <- 0 until numIns) { io.ins(i).w.ready := false.B };
  io.out.w <> io.ins(currentMaster).w

  // Unblock AW channel on last write:
  when(io.out.w.fire && io.out.w.bits.last) { wPending := false.B };

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

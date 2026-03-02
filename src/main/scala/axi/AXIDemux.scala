package axi

import chisel3._
import chisel3.util.{RRArbiter, log2Ceil}

// AXI Demultiplexer: one master port -> numOuts slave ports, routed by address.
//
// AR/AW: requests are routed to the slave port whose address range matches the transaction
// address (addrMap).  The master's ID is forwarded unchanged. Only one in-flight write
// is allowed at a time (AW gated while write pending).
//
// R/B: responses arrive from the slave ports. An RRArbiter selects among valid responses;
// IDs are passed through unchanged.
//
// W: the W channel carries no ID, so a register records the AW decode result and gates the AW
// channel when full. W must arrive at the same cycle or after its AW.
//
// cfg   -- AXIConfig for both in and outs ports (same ID width)
// numOuts -- number of slave ports
// addrMap -- address ranges for each slave port (numOuts-1 entries, last port is catch-all)
class AXIDemux(cfg: AXIConfig, numOuts: Int, addrMap: Seq[(Long, Long)]) extends Module {

  require(
    addrMap.length == numOuts - 1,
    "addrMap must have numOuts-1 entries; the last port is the default catch-all"
  )
  require(numOuts >= 1, "numOuts must be at least 1")

  val io = IO(new Bundle {
    val in = Flipped(new AXIBundle(cfg));
    val outs = Vec(numOuts, new AXIBundle(cfg));
  })

  val idxBits = log2Ceil(numOuts)

  // Write tracking: only one in-flight write allowed
  val wPending = RegInit(false.B)
  val wSel = RegInit(0.U(idxBits.W))

  // Address decode: returns the index of the slave port whose range contains addr.
  // Ports 0 .. numOuts-2 are matched against addrMap; port numOuts-1 is the catch-all.
  def decode(addr: UInt): UInt =
    addrMap.zipWithIndex.foldRight((numOuts - 1).U(idxBits.W)) { case ((entry, i), otherwise) =>
      val (base, size) = entry
      Mux(addr >= base.U && addr < (base + size).U, i.U(idxBits.W), otherwise)
    }

  // -----------------------------------------------------------------------
  // Defaults: nothing valid / nothing ready
  // -----------------------------------------------------------------------
  for (i <- 0 until numOuts) {
    // Connect input through to output:
    io.outs(i).aw.bits := io.in.aw.bits
    io.outs(i).ar.bits := io.in.ar.bits
    io.outs(i).w.bits := io.in.w.bits

    // But deassert valid / ready
    io.outs(i).ar.valid := false.B
    io.outs(i).aw.valid := false.B
    io.outs(i).w.valid := false.B
    io.outs(i).r.ready := false.B
    io.outs(i).b.ready := false.B
  }
  io.in.ar.ready := false.B
  io.in.aw.ready := false.B
  io.in.w.ready := false.B
  io.in.r.valid := false.B
  io.in.b.valid := false.B

  // -----------------------------------------------------------------------
  // AR channel: decode address, route to selected slave port
  // -----------------------------------------------------------------------
  val arSel = decode(io.in.ar.bits.addr)
  io.outs(arSel).ar.valid := io.in.ar.valid
  io.in.ar.ready := io.outs(arSel).ar.ready

  // -----------------------------------------------------------------------
  // R channel: RRArbiter over slave responses; pass through ID unchanged
  // -----------------------------------------------------------------------
  val rArb = Module(new RRArbiter(new RChan(cfg), numOuts))
  for (i <- 0 until numOuts) {
    rArb.io.in(i) <> io.outs(i).r
  }
  io.in.r.valid := rArb.io.out.valid
  io.in.r.bits := rArb.io.out.bits
  rArb.io.out.ready := io.in.r.ready

  // -----------------------------------------------------------------------
  // AW channel: decode address, gate when write is pending
  // -----------------------------------------------------------------------
  val awSel = decode(io.in.aw.bits.addr)

  // Gate AW when a write is happening:
  when(wPending) {
    io.outs(awSel).aw.valid := false.B
    io.in.aw.ready := false.B
  }.otherwise {
    io.outs(awSel).aw.valid := io.in.aw.valid
    io.in.aw.ready := io.outs(awSel).aw.ready
    when(io.in.aw.fire) {
      wPending := true.B
      wSel := awSel
    }
  }

  // -----------------------------------------------------------------------
  // W channel: route data to the pending write port
  // -----------------------------------------------------------------------
  val activeSel = Mux(wPending, wSel, awSel);
  io.outs(activeSel).w.valid := io.in.w.valid
  io.in.w.ready := io.outs(activeSel).w.ready

  // Unblock AW channel on last write:
  when(io.in.w.fire && io.in.w.bits.last) { wPending := false.B }

  // -----------------------------------------------------------------------
  // B channel: RRArbiter over slave responses; pass through ID unchanged
  // -----------------------------------------------------------------------
  val bArb = Module(new RRArbiter(new BChan(cfg), numOuts))
  for (i <- 0 until numOuts) {
    bArb.io.in(i) <> io.outs(i).b
  }
  io.in.b.valid := bArb.io.out.valid
  io.in.b.bits := bArb.io.out.bits
  bArb.io.out.ready := io.in.b.ready

}

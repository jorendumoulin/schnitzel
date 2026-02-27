package axi

import chisel3._
import chisel3.util.{Queue, RRArbiter, log2Ceil}

// Convenience constructor: derives outCfg (slave-facing, wider ID) from inCfg by widening
// idWidth by log2Ceil(numOuts).
object AXIDemux {
  def apply(cfg: AXIConfig, numOuts: Int, addrMap: Seq[(Long, Long)], maxWTrans: Int = 8): AXIDemux =
    new AXIDemux(cfg, cfg.copy(idWidth = cfg.idWidth + log2Ceil(numOuts)), numOuts, addrMap, maxWTrans)
}

// AXI Demultiplexer: one master port -> numOuts slave ports, routed by address.
//
// AR/AW: requests are routed to the slave port whose address range matches the transaction
// address (addrMap).  The master's original ID is forwarded unchanged; the downstream
// AXIMux on the slave side will prepend additional bits.
//
// R/B: responses arrive on the slave-facing outs ports with a wider ID (prepended by the
// downstream AXIMux).  An RRArbiter selects among valid responses; the prepended upper bits
// are stripped before presenting the original ID back to the master on in.
//
// W: the W channel carries no ID, so a FIFO records the AW decode result and gates the AW
// channel when full.
//
// inCfg  -- AXIConfig for the in port   (master-facing, narrower ID)
// outCfg -- AXIConfig for the outs ports (slave-facing,  wider ID)
//           outCfg.idWidth must equal inCfg.idWidth + log2Ceil(numOuts)
class AXIDemux(inCfg: AXIConfig, outCfg: AXIConfig, numOuts: Int, addrMap: Seq[(Long, Long)], maxWTrans: Int = 8)
    extends Module {

  require(
    addrMap.length == numOuts - 1,
    "addrMap must have numOuts-1 entries; the last port is the default catch-all"
  )
  require(numOuts >= 1, "numOuts must be at least 1")
  require(maxWTrans >= 1, "maxWTrans must be at least 1")
  require(
    outCfg.idWidth == inCfg.idWidth + log2Ceil(numOuts),
    s"outCfg.idWidth (${outCfg.idWidth}) must equal inCfg.idWidth (${inCfg.idWidth}) + log2Ceil(numOuts) (${log2Ceil(numOuts)})"
  )

  val io = IO(new Bundle {
    val in   = Flipped(new AXIBundle(inCfg));
    val outs = Vec(numOuts, new AXIBundle(outCfg));
  })

  val idxBits = log2Ceil(numOuts)

  // Address decode: returns the index of the slave port whose range contains addr.
  // Ports 0 .. numOuts-2 are matched against addrMap; port numOuts-1 is the catch-all.
  def decode(addr: UInt): UInt =
    addrMap.zipWithIndex.foldRight((numOuts - 1).U(idxBits.W)) {
      case ((entry, i), otherwise) =>
        val (base, size) = entry
        Mux(addr >= base.U && addr < (base + size).U, i.U(idxBits.W), otherwise)
    }

  // -----------------------------------------------------------------------
  // W FIFO: records the AW decode result; W data is routed to that port.
  // Popped on the last W beat.  AW is gated when full.
  // -----------------------------------------------------------------------
  val wFifo = Module(new Queue(UInt(idxBits.W), maxWTrans))

  // -----------------------------------------------------------------------
  // Defaults: nothing valid / nothing ready
  // -----------------------------------------------------------------------
  for (i <- 0 until numOuts) {
    io.outs(i).ar.valid := false.B
    io.outs(i).ar.bits  := io.in.ar.bits
    io.outs(i).aw.valid := false.B
    io.outs(i).aw.bits  := io.in.aw.bits
    io.outs(i).w.valid  := false.B
    io.outs(i).w.bits   := io.in.w.bits
    io.outs(i).r.ready  := false.B
    io.outs(i).b.ready  := false.B
  }
  io.in.ar.ready := false.B
  io.in.aw.ready := false.B
  io.in.w.ready  := false.B
  io.in.r.valid  := false.B
  io.in.r.bits   := io.outs(0).r.bits
  io.in.b.valid  := false.B
  io.in.b.bits   := io.outs(0).b.bits

  // -----------------------------------------------------------------------
  // AR channel: decode address, route to selected slave port
  // -----------------------------------------------------------------------
  val arSel = decode(io.in.ar.bits.addr)

  when(true.B) {
    io.outs(arSel).ar.valid := io.in.ar.valid
    io.in.ar.ready           := io.outs(arSel).ar.ready
  }

  // -----------------------------------------------------------------------
  // R channel: RRArbiter over slave responses; strip prepended upper ID bits
  // -----------------------------------------------------------------------
  val rArb = Module(new RRArbiter(new RChan(outCfg), numOuts))
  for (i <- 0 until numOuts) {
    rArb.io.in(i) <> io.outs(i).r
  }
  io.in.r.valid    := rArb.io.out.valid
  io.in.r.bits     := rArb.io.out.bits
  io.in.r.bits.id  := rArb.io.out.bits.id(inCfg.idWidth - 1, 0)
  rArb.io.out.ready := io.in.r.ready

  // -----------------------------------------------------------------------
  // AW channel: decode address, gate when W FIFO is full
  // -----------------------------------------------------------------------
  val awSel = decode(io.in.aw.bits.addr)

  wFifo.io.enq.valid := false.B
  wFifo.io.enq.bits  := awSel

  when(wFifo.io.enq.ready) {
    io.outs(awSel).aw.valid := io.in.aw.valid
    io.in.aw.ready           := io.outs(awSel).aw.ready
    when(io.in.aw.fire) {
      wFifo.io.enq.valid := true.B
    }
  }

  // -----------------------------------------------------------------------
  // W channel: route to the slave port recorded at the W FIFO head
  // -----------------------------------------------------------------------
  val wSel = wFifo.io.deq.bits

  wFifo.io.deq.ready := false.B
  when(wFifo.io.deq.valid) {
    io.outs(wSel).w.valid := io.in.w.valid
    io.in.w.ready          := io.outs(wSel).w.ready
    wFifo.io.deq.ready     := io.in.w.fire && io.in.w.bits.last
  }

  // -----------------------------------------------------------------------
  // B channel: RRArbiter over slave responses; strip prepended upper ID bits
  // -----------------------------------------------------------------------
  val bArb = Module(new RRArbiter(new BChan(outCfg), numOuts))
  for (i <- 0 until numOuts) {
    bArb.io.in(i) <> io.outs(i).b
  }
  io.in.b.valid    := bArb.io.out.valid
  io.in.b.bits     := bArb.io.out.bits
  io.in.b.bits.id  := bArb.io.out.bits.id(inCfg.idWidth - 1, 0)
  bArb.io.out.ready := io.in.b.ready

}

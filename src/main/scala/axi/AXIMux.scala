package axi

import chisel3._
import chisel3.util.LockingRRArbiter
import chisel3.util.RRArbiter

class AXIMux(cfg: AXIConfig, numIns: Int) extends Module {

  val io = IO(new Bundle {
    val ins = Vec(numIns, Flipped(new AXIBundle(cfg)));
    val out = new AXIBundle(cfg);
  })

  // AR arbitration
  val arArb = Module(new RRArbiter(new ARChan(cfg), numIns));
  arArb.io.in <> io.ins.map(_.ar);
  io.out.ar <> arArb.io.out;

  // R routing
  io.out.r.ready := false.B;
  for (i <- 0 until numIns) {
    io.ins(i).r.bits <> io.out.r.bits;
    when(io.ins(i).ar.bits.id === io.out.r.bits.id) {
      io.ins(i).r.valid := io.out.r.valid;
      io.out.r.ready := io.ins(i).r.ready;
    }.otherwise {
      io.ins(i).r.valid := false.B;
    }
  }

  // AW arbitration
  val awArb = Module(new RRArbiter(new AWChan(cfg), numIns));
  awArb.io.in <> io.ins.map(_.aw);
  io.out.aw <> awArb.io.out;

  // W routing
  val w_choice = awArb.io.chosen
  // val w_choice = Reg(chiselTypeOf(awArb.io.chosen))
  // when(io.out.aw.fire) {
  //  w_choice := awArb.io.chosen
  // }
  io.out.w <> io.ins(w_choice).w;
  for (i <- 0 until numIns) {
    when(i.U === w_choice) {
      io.ins(i).w.ready := io.out.w.ready;
    }.otherwise {
      io.ins(i).w.ready := false.B;
    }
  }

  // B routing
  io.out.b.ready := false.B;
  for (i <- 0 until numIns) {
    io.ins(i).b.bits <> io.out.b.bits;
    when(io.ins(i).aw.bits.id === io.out.b.bits.id) {
      io.ins(i).b.valid := io.out.b.valid;
      io.out.b.ready := io.ins(i).b.ready;
    }.otherwise {
      io.ins(i).b.valid := false.B;
    }
  }

}

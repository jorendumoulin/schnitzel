package axi

import chisel3._
import chisel3.util.{Cat, log2Ceil, Queue}
import core.DecoupledBusIO
import chisel3.util.Decoupled
import streamer.StreamerDir.read
import chisel3.util.RRArbiter

class AxiToMem(addrWidth: Int, dataWidth: Int, axiConfig: AXIConfig) extends Module {

  val io = IO(new Bundle {
    val mem = new DecoupledBusIO(addrWidth, dataWidth);
    val axi = Flipped(new AXIBundle(axiConfig));
  })

  class Meta extends Bundle {
    val a = new AChan(axiConfig)
    val write = Bool()
    val last = Bool()
  }

  // Arbitrate between reads and writes.
  val arbiter = Module(new RRArbiter(new Meta, 2))

  // Handle reads
  val read_meta = arbiter.io.in(0)
  dontTouch(read_meta)
  val read_meta_reg = RegNext(read_meta.bits)
  dontTouch(read_meta_reg)
  val read_count = RegInit(0.U(axiConfig.lenWidth.W))

  // Default assignments
  io.axi.ar.ready := false.B
  read_meta.valid := false.B
  read_meta.bits := DontCare
  read_meta.bits.write := false.B

  // Handle R burst in progress.
  when(read_count > 0.U) {
    read_meta.bits := read_meta_reg
    read_meta.bits.last := (read_count === 1.U)
    read_meta.valid := true.B
    when(read_meta.ready) {
      read_count := read_count - 1.U;
      read_meta.bits.a.addr := read_meta_reg.a.addr + read_meta_reg.a.bytesPerBeat
    }
  }.elsewhen(io.axi.ar.valid) { // Handle new AR if there is one.
    read_meta.valid := true.B
    read_meta.bits.a := io.axi.ar.bits
    read_meta.bits.last := io.axi.ar.bits.len === 0.U
    io.axi.ar.ready := read_meta.ready
    when(read_meta.ready) { read_count := io.axi.ar.bits.len }
  }

  // Handle writes
  val write_meta = arbiter.io.in(1)
  dontTouch(write_meta)
  val write_meta_reg = RegNext(write_meta.bits)
  dontTouch(write_meta_reg)
  val write_count = RegInit(0.U(axiConfig.lenWidth.W))

  // Default assignments
  io.axi.aw.ready := false.B
  io.axi.w.ready := false.B
  write_meta.valid := false.B
  write_meta.bits := DontCare
  write_meta.bits.write := true.B

  // Handle W burst in progress.
  when(write_count > 0.U) {
    write_meta.bits := write_meta_reg
    write_meta.bits.last := (write_count === 1.U)
    when(io.axi.w.valid) {
      write_meta.valid := true.B
      when(write_meta.ready) {
        io.axi.w.ready := true.B
        write_count := write_count - 1.U;
        write_meta.bits.a.addr := write_meta_reg.a.addr + write_meta_reg.a.bytesPerBeat
      }
    }
    // TODO: this is copied from pulp, but requiring both aw and w to be valid in the same cycle
    // feels like it is way to restrictive and risks deadlocks
  }.elsewhen(io.axi.aw.valid && io.axi.w.valid) { // Handle new AW if there is one.
    write_meta.valid := true.B
    write_meta.bits.a := io.axi.aw.bits
    write_meta.bits.last := io.axi.aw.bits.len === 0.U
    when(write_meta.ready) {
      write_count := io.axi.aw.bits.len;
      io.axi.aw.ready := write_meta.ready
      io.axi.w.ready := write_meta.ready
    }
  }

  val meta = arbiter.io.out
  val metaReg = Reg(new Meta)
  when(meta.fire) { metaReg := meta.bits }

  // Create memory requests
  io.mem.req.bits.addr := meta.bits.a.addr;
  io.mem.req.bits.wen := meta.bits.write;
  io.mem.req.bits.ben := io.axi.w.bits.strb;
  io.mem.req.bits.wdata := io.axi.w.bits.data;
  io.mem.req.valid := meta.valid
  meta.ready := io.mem.req.ready

  // By default, always ready to receive response
  io.mem.rsp.ready := true.B

  // Create R responses
  io.axi.r.bits.data := io.mem.rsp.bits.data
  io.axi.r.bits.user := 0.U
  io.axi.r.bits.resp := 0.U
  io.axi.r.bits.id := metaReg.a.id
  io.axi.r.bits.last := metaReg.last
  io.axi.r.valid := io.mem.rsp.valid && ~metaReg.write
  when(~metaReg.write) { io.mem.rsp.ready := io.axi.r.ready }

  // Create B responses
  io.axi.b.bits.id := metaReg.a.id
  io.axi.b.bits.user := 0.U
  io.axi.b.bits.resp := 0.U
  io.axi.b.valid := io.mem.rsp.valid && metaReg.write && metaReg.last
  when(metaReg.write && metaReg.last) { io.mem.rsp.ready := io.axi.b.ready }

}

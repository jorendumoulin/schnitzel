package top

import chisel3._
import chisel3.util.{Cat, switch, is}
import axi.AXILiteBundle

/** Small AXI4-Lite slave for validating the PS/PL path independently of the cluster. */
class SimpleAxiClient extends RawModule {
  val aclk = IO(Input(Clock()))
  val aresetn = IO(Input(Bool()))
  val s_axi = IO(Flipped(new AXILiteBundle()))
  val trace_aw = IO(Output(UInt(14.W)))
  val trace_w  = IO(Output(UInt(34.W)))
  val trace_b  = IO(Output(UInt(4.W)))
  val trace_ar = IO(Output(UInt(14.W)))
  val trace_r  = IO(Output(UInt(36.W)))

  val logic = withClockAndReset(aclk, !aresetn) { Module(new SimpleAxiClientLogic) }
  logic.io.axi <> s_axi
  trace_aw := logic.io.trace_aw
  trace_w := logic.io.trace_w
  trace_b := logic.io.trace_b
  trace_ar := logic.io.trace_ar
  trace_r := logic.io.trace_r
}

class SimpleAxiClientLogic extends Module {
  val io = IO(new Bundle {
    val axi = Flipped(new AXILiteBundle())
    val trace_aw = Output(UInt(14.W))
    val trace_w = Output(UInt(34.W))
    val trace_b = Output(UInt(4.W))
    val trace_ar = Output(UInt(14.W))
    val trace_r = Output(UInt(36.W))
  })

  val okay = 0.U(2.W)
  val slverr = 2.U(2.W)
  val awHeld = RegInit(false.B)
  val wHeld = RegInit(false.B)
  val awaddr = RegInit(0.U(12.W))
  val wdata = RegInit(0.U(32.W))
  val wstrb = RegInit(0.U(4.W))
  val bvalid = RegInit(false.B)
  val bresp = RegInit(okay)
  val rvalid = RegInit(false.B)
  val rdata = RegInit(0.U(32.W))
  val rresp = RegInit(okay)
  val control = RegInit(0.U(32.W))
  val scratch = RegInit(0.U(32.W))
  val writeCount = RegInit(0.U(32.W))
  val readCount = RegInit(0.U(32.W))

  io.axi.aw.ready := !awHeld && !bvalid
  io.axi.w.ready := !wHeld && !bvalid
  io.axi.ar.ready := !rvalid
  io.axi.b.valid := bvalid
  io.axi.b.bits := bresp
  io.axi.r.valid := rvalid
  io.axi.r.bits.data := rdata
  io.axi.r.bits.resp := rresp

  when (io.axi.aw.fire) {
    awHeld := true.B
    awaddr := io.axi.aw.bits.addr
  }
  when (io.axi.w.fire) {
    wHeld := true.B
    wdata := io.axi.w.bits.data
    wstrb := io.axi.w.bits.strb
  }
  when (io.axi.b.fire) { bvalid := false.B }
  when (io.axi.r.fire) { rvalid := false.B }

  when (awHeld && wHeld && !bvalid) {
    awHeld := false.B
    wHeld := false.B
    bvalid := true.B
    bresp := slverr
    writeCount := writeCount + 1.U
    switch (awaddr) {
      is (0x00.U) {
        bresp := okay
        when (wstrb(0)) { control := wdata }
      }
      is (0x04.U) {
        bresp := okay
        when (wstrb(0)) { scratch := wdata }
      }
    }
  }

  when (io.axi.ar.fire) {
    rvalid := true.B
    rdata := 0.U
    rresp := slverr
    readCount := readCount + 1.U
    switch (io.axi.ar.bits.addr) {
      is (0x00.U) { rdata := control; rresp := okay }
      is (0x04.U) { rdata := scratch; rresp := okay }
      is (0x08.U) { rdata := writeCount; rresp := okay }
      is (0x0c.U) { rdata := readCount; rresp := okay }
    }
  }

  io.trace_aw := Cat(io.axi.aw.valid, io.axi.aw.ready, io.axi.aw.bits.addr)
  io.trace_w := Cat(io.axi.w.valid, io.axi.w.ready, io.axi.w.bits.data(31, 0))
  io.trace_b := Cat(io.axi.b.valid, io.axi.b.ready, io.axi.b.bits)
  io.trace_ar := Cat(io.axi.ar.valid, io.axi.ar.ready, io.axi.ar.bits.addr)
  io.trace_r := Cat(io.axi.r.valid, io.axi.r.ready, io.axi.r.bits.data(31, 0), io.axi.r.bits.resp)
}

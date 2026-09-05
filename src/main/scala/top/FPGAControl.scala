package top

import chisel3._
import chisel3.util._
import axi.AXILiteBundle
import csr.CsrIO

/** ARM control registers. See fpga/README.md for the software contract. */
class FPGAControl extends Module {
  val io = IO(new Bundle {
    val axi = Flipped(new AXILiteBundle())
    val csr = Flipped(new CsrIO)
    val run = Output(Bool())
    val axiError = Input(Bool())
  })

  val okay = 0.U(2.W)
  val slverr = 2.U(2.W)
  val run = RegInit(false.B)
  val releasePending = RegInit(false.B)
  val barrierCount = RegInit(0.U(32.W))
  val axiError = RegInit(false.B)
  val barrierWaiting = run && io.csr.req.valid && io.csr.req.bits.addr === 0.U

  io.run := run
  // CsrCombiner broadcasts ready, so qualify it with the combined valid.
  io.csr.req.ready := !reset.asBool && barrierWaiting && releasePending
  io.csr.rsp.rdata := 0.U

  // Hold AW and W independently, accepting either ordering. One write at a time.
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

  io.axi.aw.ready := !reset.asBool && !awHeld && !bvalid
  io.axi.w.ready := !reset.asBool && !wHeld && !bvalid
  io.axi.ar.ready := !reset.asBool && !rvalid
  io.axi.b.valid := bvalid
  io.axi.b.bits := bresp
  io.axi.r.valid := rvalid
  io.axi.r.bits.data := rdata
  io.axi.r.bits.resp := rresp

  when(io.axi.aw.fire) {
    awaddr := io.axi.aw.bits.addr
    awHeld := true.B
  }
  when(io.axi.w.fire) {
    wdata := io.axi.w.bits.data
    wstrb := io.axi.w.bits.strb
    wHeld := true.B
  }
  when(io.axi.b.fire) { bvalid := false.B }
  when(io.axi.r.fire) { rvalid := false.B }

  when(io.csr.req.fire) {
    releasePending := false.B
    barrierCount := barrierCount + 1.U
  }

  when(awHeld && wHeld && !bvalid) {
    awHeld := false.B
    wHeld := false.B
    bvalid := true.B
    bresp := slverr
    switch(awaddr) {
      is(0x00.U) {
        bresp := okay
        when(wstrb(0)) {
          run := wdata(0)
          when(!wdata(0)) {
            releasePending := false.B
            barrierCount := 0.U
          }
        }
      }
      is(0x08.U) {
        bresp := okay
        when(wstrb(0) && wdata(0)) {
          when(run) { releasePending := true.B }
            .otherwise { bresp := slverr }
        }
      }
      is(0x10.U) {
        bresp := okay
        when(wstrb(0) && wdata(0)) { axiError := false.B }
      }
    }
  }
  // Newly observed errors win over a simultaneous software clear.
  when(io.axiError) { axiError := true.B }

  when(io.axi.ar.fire) {
    rvalid := true.B
    rdata := 0.U
    rresp := slverr
    switch(io.axi.ar.bits.addr) {
      is(0x00.U) { rdata := run; rresp := okay }
      is(0x04.U) { rdata := Cat(releasePending, barrierWaiting, run); rresp := okay }
      is(0x08.U) { rdata := releasePending; rresp := okay }
      is(0x0c.U) { rdata := barrierCount; rresp := okay }
      is(0x10.U) { rdata := axiError; rresp := okay }
    }
  }
}

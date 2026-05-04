package axi

import chisel3._
import chisel3.util.{Cat, log2Ceil, Queue}
import core.DecoupledBusIO

class DecoupledIOToAXI(addrWidth: Int, dataWidth: Int, axiConfig: AXIConfig, id: Int) extends Module {

  val io = IO(new Bundle {
    val bus = Flipped(new DecoupledBusIO(addrWidth, dataWidth));
    val axi = new AXIBundle(axiConfig);
  })

  val addrAlignment: Int = log2Ceil(axiConfig.dataWidth / 8);

  // AW Channel
  io.axi.aw.bits.id := id.U;
  io.axi.aw.bits.addr := Cat(io.bus.req.bits.addr(addrWidth - 1, addrAlignment), 0.U(addrAlignment.W));
  io.axi.aw.bits.len := 0.U; // nb bytes
  io.axi.aw.bits.size := log2Ceil(dataWidth / 8).U; // nb bytes per beat
  io.axi.aw.bits.burst := 0.U; // type of beat
  io.axi.aw.bits.lock := 0.U;
  io.axi.aw.bits.cache := 0.U;
  io.axi.aw.bits.prot := 0.U;
  io.axi.aw.bits.qos := 0.U;
  io.axi.aw.bits.region := 0.U;
  io.axi.aw.bits.user := 0.U;
  io.axi.aw.valid := io.bus.req.valid && io.bus.req.bits.wen;

  val wIndex = Wire(UInt(log2Ceil(axiConfig.dataWidth / dataWidth).W))
  wIndex := io.bus.req.bits.addr(5, 2)

  // Data queue:& ~((axiConfig.dataWidth / 8 - 1).U);
  class DataQueue extends Bundle {
    val wdata = chiselTypeOf(io.bus.req.bits.wdata)
    val ben = chiselTypeOf(io.bus.req.bits.ben)
  }
  val data_queue = Module(new Queue(new DataQueue, 2, flow = true))
  data_queue.io.enq.bits.wdata := io.bus.req.bits.wdata
  data_queue.io.enq.bits.ben := io.bus.req.bits.ben
  val awReady = io.axi.aw.ready && data_queue.io.enq.ready;
  val stale_data = RegNext(io.bus.req.valid && ~io.axi.w.fire)
  data_queue.io.enq.valid := io.bus.req.valid && io.bus.req.bits.wen && ~stale_data

  // W channel
  data_queue.io.deq.ready := io.axi.w.ready;
  io.axi.w.valid := data_queue.io.deq.valid;
  val data = Wire(Vec((axiConfig.dataWidth / dataWidth), UInt(dataWidth.W)))
  data := 0.U.asTypeOf(chiselTypeOf(data))
  data(wIndex) := data_queue.io.deq.bits.wdata;
  val strobe = Wire(Vec((axiConfig.dataWidth / dataWidth), UInt((dataWidth / 8).W)))
  strobe := 0.U.asTypeOf(chiselTypeOf(strobe))
  strobe(wIndex) := data_queue.io.deq.bits.ben;
  io.axi.w.bits.data := data.asUInt;
  io.axi.w.bits.strb := strobe.asUInt;
  io.axi.w.bits.last := true.B;
  io.axi.w.bits.user := 0.U;

  // B Channel:
  io.axi.b := DontCare
  io.axi.b.ready := true.B;

  // AR Channel
  io.axi.ar.bits.id := id.U;
  io.axi.ar.bits.addr := Cat(io.bus.req.bits.addr(addrWidth - 1, addrAlignment), 0.U(addrAlignment.W));
  io.axi.ar.bits.len := 0.U; // = (burst size - 1)
  io.axi.ar.bits.size := log2Ceil(dataWidth / 8).U; // nb beats
  io.axi.ar.bits.burst := 0.U; // type of beat
  io.axi.ar.bits.lock := 0.U;
  io.axi.ar.bits.cache := 0.U;
  io.axi.ar.bits.prot := 0.U;
  io.axi.ar.bits.qos := 0.U;
  io.axi.ar.bits.region := 0.U;
  io.axi.ar.bits.user := 0.U;
  io.axi.ar.valid := io.bus.req.valid && ~io.bus.req.bits.wen;
  val arReady = io.axi.ar.ready

  val rIndex = Reg(UInt(log2Ceil(axiConfig.dataWidth / dataWidth).W))
  val expectingR = RegInit(false.B)
  when(io.axi.ar.fire) {
    rIndex := io.bus.req.bits.addr(5, 2)
  }

  io.bus.req.ready := Mux(io.bus.req.bits.wen, awReady, arReady);

  // R channel
  when(io.axi.ar.fire) { expectingR := true.B }.elsewhen(io.bus.rsp.fire) { expectingR := false.B }
  io.bus.rsp.valid := io.axi.r.valid || io.axi.b.valid; io.axi.r.ready := io.bus.rsp.ready && expectingR;
  val rdata = io.axi.r.bits.data.asTypeOf(Vec((axiConfig.dataWidth / dataWidth), UInt(dataWidth.W)))
  io.bus.rsp.bits.data := rdata(rIndex)

}

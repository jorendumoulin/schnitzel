package icache

import chisel3._
import chisel3.util.{Cat, Decoupled, LockingRRArbiter, MuxLookup, MemoryReadWritePort}
import core.{DecoupledBusIO, CoreConfig}
import icache.{IReq, IRsp, ICacheConfig}
import icache.ICacheRsp
import icache.BankPort
import chisel3.util.SRAM
import icache.ICacheRead
import core.BusReq

// serve = Serving Cache Requests
// req = Made outside request for long cache line
// wait = Waiting for outside cache request to arrive
// fill = Filling up the cache with received outside data
object ICacheState extends ChiselEnum { val serve, req, axi = Value }

class ICache(numInp: Int = 1) extends Module {

  val cfg = ICacheConfig;

  val io = IO(new Bundle {
    // incoming instruction requests
    val imems = Vec(numInp, Flipped(new DecoupledBusIO(CoreConfig.addrWidth, CoreConfig.instrWidth)))
    // outgoing axi requests
    val axi = new DecoupledBusIO(32, 512);
  })

  // FSM state of icache
  val state = RegInit(ICacheState.serve);
  dontTouch(state);

  // Arbitrate requests
  val arbiter = Module(new LockingRRArbiter(new BusReq(CoreConfig.addrWidth, CoreConfig.instrWidth), numInp, 32))
  arbiter.io.in <> VecInit(io.imems.map { imem => imem.req })
  val req = arbiter.io.out;
  // Ready for requests when in serving state
  req.ready := (state === ICacheState.serve);
  // Keep track of arbiter choice for returning responses
  val prevChoice = RegNext(arbiter.io.chosen);

  // Cache memory structure
  // valids are registers such that they can be reset at once
  val valids = RegInit(VecInit(Seq.fill(cfg.cacheLines)(false.B)))
  val tags_sram = SRAM(cfg.cacheLines, UInt(cfg.tagWidth.W), 0, 0, 1);
  val tags = tags_sram.readwritePorts(0)
  tags.enable := false.B; tags.address := DontCare; tags.isWrite := DontCare; tags.writeData := DontCare;
  val data_sram = VecInit(Seq.fill(cfg.instrsPerLine)(SRAM(cfg.cacheLines, UInt(cfg.instrWidth.W), 0, 0, 1)));
  val data_ports = VecInit(data_sram.map(sram => sram.readwritePorts(0)));
  data_ports.foreach { port =>
    port.enable := false.B; port.address := DontCare;
    port.writeData := DontCare; port.isWrite := DontCare;
  }

  // Fetch element from the cache
  val cacheRead = req.bits.addr.asTypeOf(new ICacheRead)
  when(req.fire) {
    tags.enable := true.B; tags.address := cacheRead.line; tags.isWrite := false.B;
    val port = data_ports(cacheRead.instr);
    port.enable := true.B; port.address := cacheRead.line; port.isWrite := false.B;
  }

  dontTouch(cacheRead)

  // Cache response is valid in the next cycle:
  val cacheRsp = new ICacheRsp
  cacheRsp.req := RegNext(req.fire)
  cacheRsp.valid := RegNext(valids(cacheRead.line));
  cacheRsp.tag := tags.readData;
  cacheRsp.tag_target := RegNext(cacheRead.tag);
  cacheRsp.instr_target := RegNext(cacheRead.instr);
  cacheRsp.instr_data := data_ports(cacheRsp.instr_target).readData;

  // Cache responses
  io.imems.foreach(imem => { imem.rsp.valid := false.B; imem.rsp.bits.data := DontCare; });
  io.imems(prevChoice).rsp.bits.data := cacheRsp.instr_data;
  io.imems(prevChoice).rsp.valid := cacheRsp.hit;

  // Cache misses
  // Keep track of the cache miss to send out outside request:
  val cacheMiss = Reg(new ICacheRead);
  cacheMiss := Mux(req.fire, cacheRead, cacheMiss);

  val abcd = state === ICacheState.serve && cacheRsp.miss;
  dontTouch(abcd);
  // Go to req state, do not accept any requests anymore
  when(abcd) {
    state := ICacheState.req;
    req.ready := false.B
  }

  // Send out AXI req for new cache line
  when(cacheRsp.miss || state === ICacheState.req) {
    io.axi.req.valid := true.B
    io.axi.req.bits.addr := Cat(cacheMiss.tag, cacheMiss.line, 0.U(ICacheConfig.instrBits.W + ICacheConfig.byteBits.W))
    io.axi.req.bits.wen := false.B
    io.axi.req.bits.ben := 1.U.asTypeOf(chiselTypeOf(io.axi.req.bits.ben));
    io.axi.req.bits.wdata := DontCare
  }.otherwise {
    io.axi.req.valid := false.B;
    io.axi.req.bits := DontCare
  }

  // wait for AXI rsp on accepted request
  when(io.axi.req.fire) { state := ICacheState.axi };

  // Write back AXI rsp:
  io.axi.rsp.ready := state === ICacheState.axi;
  when(io.axi.rsp.fire) {
    valids(cacheMiss.line) := true.B;
    tags.enable := true.B; tags.address := cacheMiss.line; tags.isWrite := true.B;
    tags.writeData := cacheMiss.tag;
    val instrs = io.axi.rsp.bits.data.asTypeOf(Vec(cfg.instrsPerLine, UInt(cfg.instrWidth.W)));
    data_ports.zip(instrs).foreach { case (port, instr) =>
      // val port = sram.readwritePorts(0);
      port.enable := true.B; port.address := cacheMiss.line; port.isWrite := true.B;
      port.writeData := instr;
    }

    // Serve result of miss as valid response:
    io.imems(prevChoice).rsp.bits.data := instrs(cacheMiss.instr);
    io.imems(prevChoice).rsp.valid := true.B;
    state := ICacheState.serve;
  }

}

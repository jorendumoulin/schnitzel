package streamer

import chisel3._
import chisel3.util.Queue
import core.DecoupledBusIO
import chisel3.util.{Decoupled, RRArbiter}
import dataclass.data
import streamer.AguOutput
import core.BusReq

object StreamerDir extends ChiselEnum { val read, write, readWrite = Value }

class Streamer(
    nTemporalDims: Int,
    spatialDimSizes: Seq[Int],
    queueDepth: Int = 2,
    addrWidth: Int = 32,
    dataWidth: Int = 64
) extends Module {

  val numPorts = spatialDimSizes.fold(1)(_ * _)
  val streamerDataType = UInt((numPorts * dataWidth).W)

  val io = IO(new Bundle {
    val start = Input(Bool())
    val config = Input(new AffineAguConfig(nTemporalDims, spatialDimSizes))
    val tcdmReqs = Vec(numPorts, new DecoupledBusIO(addrWidth, dataWidth))
    val dir = Input(StreamerDir())
    val readData = Decoupled(streamerDataType)
    val writeData = Flipped(Decoupled(streamerDataType))
    val done = Output(Bool())
  })

  dontTouch(io.config)

  val agu = Module(new AffineAgu(nTemporalDims, spatialDimSizes, queueDepth));
  agu.io.start := io.start
  agu.io.config := io.config

  // --- Bypass buffer state machine for readWrite (reduction) mode ---
  // TCDM:   first iteration, readData sourced from TCDM response queue
  // Bypass: subsequent iterations, readData sourced from bypass buffer
  object BypassState extends ChiselEnum { val tcdm, bypass = Value }
  val bypassState = RegInit(BypassState.tcdm)
  val bypassBuffer = Reg(Vec(numPorts, UInt(dataWidth.W)))
  // Tracks whether bypass data has been consumed this iteration,
  // preventing the accelerator from seeing multiple valid pulses for the same data
  val bypassConsumed = RegInit(false.B)
  val inReadWrite = io.dir === StreamerDir.readWrite

  // Split full-width read/write ports into data port widths:
  val readVec = Wire(Vec(numPorts, UInt(dataWidth.W)))
  io.readData.bits := readVec.asTypeOf(streamerDataType)
  val writeVec = io.writeData.bits.asTypeOf(Vec(numPorts, UInt(dataWidth.W)))

  // Read/write request arbiter per port
  val readWriteArbiters = (0 until numPorts).map { i =>
    val readWriteArbiter = Module(new RRArbiter(new BusReq(addrWidth, dataWidth), 2))
    // Attach each arbiters output to the req part of a TCDM port
    io.tcdmReqs(i).req <> readWriteArbiter.io.out
    readWriteArbiter
  }

  // Queue to request reads from TCDM
  val readReqQueues = (0 until numPorts).map { i =>
    val readReqQueue = Module(new Queue(new BusReq(addrWidth, dataWidth), queueDepth))
    // read addresses are queued per port indidvidually
    readReqQueue.io.enq.bits.addr := agu.io.addrs.bits.addrs(i)
    readReqQueue.io.enq.bits.wdata := DontCare
    readReqQueue.io.enq.bits.wen := false.B;
    readReqQueue.io.enq.bits.ben := VecInit(Seq.fill(dataWidth / 8)(true.B)).asUInt
    // Only queue if the streamer is reading and, when reducing if it is the first address
    readReqQueue.io.enq.valid := agu.io.addrs.valid && agu.io.addrs.bits.isFirst && ((io.dir === StreamerDir.read) || (io.dir === StreamerDir.readWrite))
    // port 0 on arbiter is for reads
    readWriteArbiters(i).io.in(0) <> readReqQueue.io.deq
    readReqQueue
  }

  // Queue to request writes to TCDM
  val writeReqQueues = (0 until numPorts).map { i =>
    // Convert write queue outputs to request
    // port 1 on arbiter is for writes
    val writeReqQueue = Module(new Queue(new BusReq(addrWidth, dataWidth), queueDepth))
    writeReqQueue.io.enq.bits.addr := agu.io.addrs.bits.addrs(i)
    writeReqQueue.io.enq.bits.wdata := writeVec(i)
    writeReqQueue.io.enq.bits.wen := true.B;
    writeReqQueue.io.enq.bits.ben := VecInit(Seq.fill(dataWidth / 8)(true.B)).asUInt
    // Only queue if the streamer is writing and, when reducing if it is the last address
    // Also gate on writeData.valid to ensure we capture valid data (not garbage)
    writeReqQueue.io.enq.valid := agu.io.addrs.valid && io.writeData.valid && agu.io.addrs.bits.isLast && ((io.dir === StreamerDir.write) || (io.dir === StreamerDir.readWrite))
    // port 1 on arbiter is for writes
    readWriteArbiters(i).io.in(1) <> writeReqQueue.io.deq
    writeReqQueue
  }

  // Combine many ready/valid into one:
  val allReadReqQueuesReady = readReqQueues.map(_.io.enq.ready).reduce(_ && _)
  val allWriteReqQueuesReady = writeReqQueues.map(_.io.enq.ready).reduce(_ && _)

  // Wait for one or multiple queues (based on mode) before requesting new addresses
  // In write/readWrite modes, also wait for writeData.valid so addresses stay in sync with data
  when(io.dir === StreamerDir.write) {
    agu.io.addrs.ready := allWriteReqQueuesReady && io.writeData.valid
  }.elsewhen(io.dir === StreamerDir.read) {
    agu.io.addrs.ready := allReadReqQueuesReady
  }.otherwise { // readWrite
    agu.io.addrs.ready := allReadReqQueuesReady && allWriteReqQueuesReady && io.writeData.valid
  }

  // writeData.ready depends on mode:
  // - write: ready when write queues can accept
  // - readWrite: ready when both queues can accept (keeps AGU and data in sync)
  // - read: not used
  when(io.dir === StreamerDir.write) {
    io.writeData.ready := allWriteReqQueuesReady
  }.elsewhen(inReadWrite) {
    io.writeData.ready := allReadReqQueuesReady && allWriteReqQueuesReady
  }.otherwise {
    io.writeData.ready := false.B
  }

  // --- Bypass buffer: capture writeData on non-last iterations ---
  when(inReadWrite && io.writeData.fire && !agu.io.addrs.bits.isLast) {
    bypassBuffer := writeVec
  }

  // --- Bypass state transitions ---
  when(!inReadWrite) {
    bypassState := BypassState.tcdm
  }.elsewhen(io.writeData.fire) {
    when(agu.io.addrs.bits.isLast) {
      bypassState := BypassState.tcdm
    }.otherwise {
      bypassState := BypassState.bypass
    }
  }

  // --- bypassConsumed: ensure readData fires exactly once per bypass iteration ---
  when(bypassState =/= BypassState.bypass) {
    bypassConsumed := false.B
  }.elsewhen(io.readData.fire) {
    bypassConsumed := true.B
  }.elsewhen(io.writeData.fire) {
    // Accelerator produced result, bypass buffer updated, ready for next read
    bypassConsumed := false.B
  }

  // --- Response queues and readData muxing ---
  val rspQueues = (0 until numPorts).map { i =>
    // Decouple tcdm rsps and data rsps through queues:
    val rspQueue = Module(new Queue(UInt(dataWidth.W), queueDepth))
    rspQueue.io.enq.bits := io.tcdmReqs(i).rsp.bits.data

    // readVec source: bypass buffer in bypass state, rspQueue otherwise
    when(inReadWrite && bypassState === BypassState.bypass) {
      readVec(i) := bypassBuffer(i)
    }.otherwise {
      readVec(i) := rspQueue.io.deq.bits
    }

    // Accept TCDM responses: in read mode always, in readWrite only during TCDM state
    rspQueue.io.enq.valid := io.tcdmReqs(i).rsp.valid && (
      io.dir === StreamerDir.read ||
      (inReadWrite && bypassState === BypassState.tcdm)
    )

    // Acknowledge TCDM responses: in bypass state, discard write responses
    when(inReadWrite && bypassState === BypassState.bypass) {
      io.tcdmReqs(i).rsp.ready := true.B
    }.otherwise {
      io.tcdmReqs(i).rsp.ready := rspQueue.io.enq.ready
    }

    rspQueue
  }

  // readData.valid: in bypass mode, valid when buffer hasn't been consumed yet
  val allRspValid = rspQueues.map(_.io.deq.valid).reduce(_ && _)
  when(inReadWrite && bypassState === BypassState.bypass) {
    io.readData.valid := !bypassConsumed
  }.otherwise {
    io.readData.valid := allRspValid
  }

  // rspQueue dequeue: don't dequeue in bypass mode (data comes from bypass buffer)
  rspQueues.foreach { q =>
    when(inReadWrite && bypassState === BypassState.bypass) {
      q.io.deq.ready := false.B
    }.otherwise {
      q.io.deq.ready := io.readData.ready && allRspValid
    }
  }

  // Only signal done when agu is done and all queues are empty
  val allRspEmpty = rspQueues.map(_.io.count === 0.U).reduce(_ && _)
  io.done := agu.io.done && allRspEmpty
}

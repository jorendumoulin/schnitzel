package streamer

import chisel3._
import chisel3.util.Queue
import core.DecoupledBusIO
import chisel3.util.{Decoupled, RRArbiter, log2Ceil}
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

  // In readWrite mode, the AGU doesn't advance on isFirst until writeData fires,
  // but the readReqQueue must issue the TCDM read exactly once before that.
  // This register prevents duplicate enqueues while the AGU is stalled.
  val firstReadIssued = RegInit(false.B)

  // Queue to request reads from TCDM
  // For the reads, no data is necessary, so we just make a queue of addresses instead
  val readReqQueues = (0 until numPorts).map { i =>
    val readReqQueue = Module(new Queue(UInt(addrWidth.W), queueDepth))
    readReqQueue.io.enq.bits := agu.io.addrs.bits.addrs(i)
    readReqQueue.io.enq.valid := agu.io.addrs.valid && agu.io.addrs.bits.isFirst && (
      (io.dir === StreamerDir.read) ||
        (io.dir === StreamerDir.readWrite && !firstReadIssued)
    )
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
    writeReqQueue
  }

  // Read/write request arbiter per port
  val reqArbiters = (0 until numPorts).map { i =>
    val reqArbiter = Module(new RRArbiter(new BusReq(addrWidth, dataWidth), 2))
    // Attach each arbiters output to the req part of a TCDM port
    io.tcdmReqs(i).req <> reqArbiter.io.out
    // port 0 on arbiter is for reads, only connect address, rest is hardcoded anyways
    readReqQueues(i).io.deq.ready := reqArbiter.io.in(0).ready
    reqArbiter.io.in(0).valid := readReqQueues(i).io.deq.valid
    reqArbiter.io.in(0).bits.addr := readReqQueues(i).io.deq.bits
    reqArbiter.io.in(0).bits.wdata := DontCare
    reqArbiter.io.in(0).bits.wen := false.B;
    reqArbiter.io.in(0).bits.ben := VecInit(Seq.fill(dataWidth / 8)(true.B)).asUInt
    // port 1 on arbiter is for writes
    reqArbiter.io.in(1) <> writeReqQueues(i).io.deq
    reqArbiter
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

  // --- firstReadIssued: prevent duplicate readReqQueue enqueues in readWrite mode ---
  // Cleared when AGU advances (new address) or when not in readWrite mode
  // Set when readReqQueues accept the isFirst address
  when(!inReadWrite || agu.io.addrs.fire) {
    firstReadIssued := false.B
  }.elsewhen(readReqQueues.map(_.io.enq.fire).reduce(_ && _)) {
    firstReadIssued := true.B
  }

  // --- bypassConsumed: ensure readData fires exactly once per bypass iteration ---
  // writeData.fire must take priority over readData.fire because the ALU is
  // combinational: both fire in the same cycle. writeData.fire means new data
  // has been written to the bypass buffer and is ready to be consumed next.
  when(bypassState =/= BypassState.bypass) {
    bypassConsumed := false.B
  }.elsewhen(io.writeData.fire) {
    // New result in bypass buffer, ready for next read
    bypassConsumed := false.B
  }.elsewhen(io.readData.fire) {
    bypassConsumed := true.B
  }

  // --- Track pending read responses per port ---
  // In readWrite mode, both reads and writes share the TCDM port via the arbiter.
  // We must only accept responses for reads (not writes) into the rspQueue.
  // Track outstanding reads: increment when a read request is sent to TCDM
  // (readReqQueue dequeues via arbiter), decrement when a response is accepted.
  val pendingReads = RegInit(VecInit(Seq.fill(numPorts)(0.U(log2Ceil(queueDepth + 2).W))))

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

    // Accept TCDM responses into rspQueue:
    // - read mode: accept all responses (only reads are issued)
    // - readWrite mode: only accept when we have pending read responses
    rspQueue.io.enq.valid := io.tcdmReqs(i).rsp.valid && (
      io.dir === StreamerDir.read ||
        (inReadWrite && pendingReads(i) > 0.U)
    )

    // Acknowledge TCDM responses:
    // - bypass state: discard all (no TCDM activity expected)
    // - readWrite with no pending reads: discard (it's a write response)
    // - otherwise: accept into rspQueue
    when(inReadWrite && bypassState === BypassState.bypass) {
      io.tcdmReqs(i).rsp.ready := true.B
    }.elsewhen(inReadWrite && pendingReads(i) === 0.U) {
      io.tcdmReqs(i).rsp.ready := true.B // Discard write responses
    }.otherwise {
      io.tcdmReqs(i).rsp.ready := rspQueue.io.enq.ready
    }

    rspQueue
  }

  // Update pending read counters (after rspQueues are defined so we can reference enq.fire)
  for (i <- 0 until numPorts) {
    val readSent = readReqQueues(i).io.deq.fire
    val readRspAccepted = rspQueues(i).io.enq.fire
    when(readSent && !readRspAccepted) {
      pendingReads(i) := pendingReads(i) + 1.U
    }.elsewhen(!readSent && readRspAccepted) {
      pendingReads(i) := pendingReads(i) - 1.U
    }
    // Both fire simultaneously: no change (one in, one out)
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

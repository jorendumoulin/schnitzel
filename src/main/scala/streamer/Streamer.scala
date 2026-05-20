package streamer

import chisel3._
import chisel3.util.Queue
import core.DecoupledBusIO
import chisel3.util.{Decoupled, RRArbiter, log2Ceil, log2Up}
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
    val spatialDimMask = Input(Vec(spatialDimSizes.length, Bool()))
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

  // A port is disabled if any masked-off dim has dimIndex != 0 for that port.
  // The dimIndex==0 "representative" keeps the port live; duplicates are gated.
  val laneEnabled = VecInit((0 until numPorts).map { outputIdx =>
    var multiplier = 1
    val checks = for (dim <- spatialDimSizes.indices) yield {
      val dimSize = spatialDimSizes(dim)
      val dimIndex = (outputIdx / multiplier) % dimSize
      multiplier = multiplier * dimSize
      if (dimIndex == 0) true.B else io.spatialDimMask(dim)
    }
    checks.foldLeft(true.B)(_ && _)
  })

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
  // Generalized below to gate pure-read mode too, so a stalled AGU never
  // re-enqueues the same address (which would also miscount credits).
  val firstReadIssued = RegInit(false.B)

  // Per-lane credit tracking: counts free rspQueue slots accounting for
  // in-flight reqs. Decremented when a req is admitted to readReqQueue (a
  // future rsp committed to land in rspQueue), incremented when rspQueue
  // drains. Gating both readReqQueue.enq.valid and AGU.addrs.ready on
  // credits prevents rspQueue overflow regardless of bank-arbitration timing.
  // Necessary because the interconnect's `outs.rsp.ready` is hardwired true
  // and does not propagate back-pressure when the streamer's rspQueue is full.
  val credits = Seq.fill(numPorts)(RegInit(queueDepth.U(log2Up(queueDepth + 1).W)))

  // Queue to request reads from TCDM
  // For the reads, no data is necessary, so we just make a queue of addresses instead
  val readReqQueues = (0 until numPorts).map { i =>
    val readReqQueue = Module(new Queue(UInt(addrWidth.W), queueDepth))
    readReqQueue.io.enq.bits := agu.io.addrs.bits.addrs(i)
    readReqQueue.io.enq.valid := agu.io.addrs.valid && agu.io.addrs.bits.isFirst &&
      laneEnabled(i) && !firstReadIssued && credits(i) =/= 0.U && (
        (io.dir === StreamerDir.read) ||
          (io.dir === StreamerDir.readWrite)
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
    writeReqQueue.io.enq.valid := agu.io.addrs.valid && io.writeData.valid && agu.io.addrs.bits.isLast && laneEnabled(i) && ((io.dir === StreamerDir.write) || (io.dir === StreamerDir.readWrite))
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

  // Aggregate queue readies and mode flags
  val allReadReqQueuesReady = readReqQueues.map(_.io.enq.ready).reduce(_ && _)
  val allWriteReqQueuesReady = writeReqQueues.map(_.io.enq.ready).reduce(_ && _)
  val isRead = io.dir === StreamerDir.read
  val isWrite = io.dir === StreamerDir.write
  val inBypass = inReadWrite && bypassState === BypassState.bypass

  // agu.ready: only wait for the queues actually exercised this iter. In
  // readWrite, writeData.valid paces the AGU with the ALU so every iteration
  // produces one ALU beat (otherwise iter 0 races ahead and we lose an
  // accumulation in reductions).
  val needsRead = isRead || (inReadWrite && agu.io.addrs.bits.isFirst)
  val needsWrite = isWrite || (inReadWrite && agu.io.addrs.bits.isLast)

  // Hold off the AGU until every enabled lane has a credit. Without this, the
  // AGU could issue an addr whose rsp would arrive on a full rspQueue and be
  // silently dropped at the input boundary.
  val allLaneCreditsAvailable = credits.zip(laneEnabled).map {
    case (c, en) => !en || c =/= 0.U
  }.reduce(_ && _)

  agu.io.addrs.ready :=
    (!needsRead || (allReadReqQueuesReady && allLaneCreditsAvailable)) &&
      (!needsWrite || allWriteReqQueuesReady) &&
      (isRead || io.writeData.valid)

  // writeData.ready: write mode needs only writeReq; readWrite also needs
  // readReq to keep address/data in lockstep. Read mode never consumes.
  io.writeData.ready := (isWrite && allWriteReqQueuesReady) ||
    (inReadWrite && allReadReqQueuesReady && allWriteReqQueuesReady)

  // Capture non-last writeData into the bypass buffer
  when(inReadWrite && io.writeData.fire && !agu.io.addrs.bits.isLast) {
    bypassBuffer := writeVec
  }

  // Bypass FSM: enter on non-last writeData.fire, exit on isLast or leaving readWrite
  when(!inReadWrite || (io.writeData.fire && agu.io.addrs.bits.isLast)) {
    bypassState := BypassState.tcdm
  }.elsewhen(io.writeData.fire) {
    bypassState := BypassState.bypass
  }

  // Prevent duplicate readReqQueue enqueues while AGU stalls. Reset on AGU
  // advance (next address available); set when every enabled lane has
  // enqueued for the current address. Generalized to all modes (was
  // previously gated on inReadWrite, which left pure-read mode unprotected
  // and allowed the same address to be re-enqueued each cycle during a
  // partial-stall — wasted bandwidth and broken credit accounting).
  when(agu.io.addrs.fire) {
    firstReadIssued := false.B
  }.elsewhen(readReqQueues.zip(laneEnabled).map { case (q, en) => q.io.enq.fire || !en }.reduce(_ && _)) {
    firstReadIssued := true.B
  }

  // bypassConsumed: gate readData.valid to one pulse per bypass iter.
  // writeData.fire wins same-cycle ties (new result ready for next read).
  when(!inBypass || io.writeData.fire) {
    bypassConsumed := false.B
  }.elsewhen(io.readData.fire) {
    bypassConsumed := true.B
  }

  // In readWrite, read and write requests share one TCDM port via the arbiter,
  // so rspQueue must reject write responses. readPending tracks whether an
  // outstanding read is in flight (1-bit suffices for 1-cycle TCDM latency).
  val readPending = RegInit(VecInit(Seq.fill(numPorts)(false.B)))

  val rspQueues = (0 until numPorts).map { i =>
    val rspQueue = Module(new Queue(UInt(dataWidth.W), queueDepth))
    rspQueue.io.enq.bits := io.tcdmReqs(i).rsp.bits.data
    readVec(i) := Mux(inBypass, bypassBuffer(i), rspQueue.io.deq.bits)
    rspQueue.io.enq.valid := io.tcdmReqs(i).rsp.valid && (isRead || (inReadWrite && readPending(i)))
    // Ack TCDM rsp when in bypass (nothing expected), when it's a write rsp to discard,
    // or when the rspQueue has room.
    io.tcdmReqs(i).rsp.ready := (inReadWrite && (inBypass || readPending(i))) || rspQueue.io.enq.ready
    rspQueue
  }

  // readPending toggles: xor of req-fire and rsp-fire captures "only one side moved"
  for (i <- 0 until numPorts) {
    when(readReqQueues(i).io.deq.fire =/= rspQueues(i).io.enq.fire) {
      readPending(i) := readReqQueues(i).io.deq.fire
    }
  }

  // Credit update: decrement when a req is admitted (a future rsp committed to
  // land in this lane's rspQueue), increment when a rsp is drained. When both
  // happen the same cycle the credit is unchanged. Initial value = queueDepth
  // matches an empty rspQueue with no in-flight reqs.
  for (i <- 0 until numPorts) {
    val reqAdmitted = readReqQueues(i).io.enq.fire
    val rspDrained = rspQueues(i).io.deq.fire
    when(reqAdmitted && !rspDrained) {
      credits(i) := credits(i) - 1.U
    }.elsewhen(!reqAdmitted && rspDrained) {
      credits(i) := credits(i) + 1.U
    }
  }

  // Disabled lanes never issue requests, so their rspQueues stay empty.
  // Treat them as "trivially valid" so they don't block readData.valid.
  val allRspValid = rspQueues.zip(laneEnabled).map { case (q, en) => q.io.deq.valid || !en }.reduce(_ && _)
  io.readData.valid := Mux(inBypass, !bypassConsumed, allRspValid)
  rspQueues.foreach { q => q.io.deq.ready := !inBypass && io.readData.ready && allRspValid }

  val allRspEmpty = rspQueues.map(_.io.count === 0.U).reduce(_ && _)
  io.done := agu.io.done && allRspEmpty
}

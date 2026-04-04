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
  // Wait for writeQueue to receive new write data
  io.writeData.ready := allWriteReqQueuesReady // FIXME: Should this also wait for reads to make sure data doesn't unsync with addresses?

  val rspQueues = (0 until numPorts).map { i =>
    // Decouple tcdm rsps and data rsps through queues:
    val rspQueue = Module(new Queue(UInt(dataWidth.W), queueDepth))
    readVec(i) := rspQueue.io.deq.bits
    rspQueue.io.enq.valid := io.tcdmReqs(i).rsp.valid && io.dir === StreamerDir.read
    io.tcdmReqs(i).rsp.ready := rspQueue.io.enq.ready
    rspQueue.io.enq.bits := io.tcdmReqs(i).rsp.bits.data
    rspQueue
  }

  // Combine many ready/valid into one:
  val allRspValid = rspQueues.map(_.io.deq.valid).reduce(_ && _)
  io.readData.valid := allRspValid
  rspQueues.foreach(_.io.deq.ready := io.readData.ready && allRspValid)

  // Only signal done when agu is done and all queues are empty
  val allRspEmty = rspQueues.map(_.io.count === 0.U).reduce(_ && _)
  io.done := agu.io.done && allRspEmty
}

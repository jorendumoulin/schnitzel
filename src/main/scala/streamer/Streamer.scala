package streamer

import chisel3._
import chisel3.util.Queue
import core.DecoupledBusIO
import chisel3.util.Decoupled
import dataclass.data

object StreamerDir extends ChiselEnum { val read, write = Value }

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
    val read = Decoupled(streamerDataType)
    val write = Flipped(Decoupled(streamerDataType))
    val done = Output(Bool())
  })

  dontTouch(io.config)

  val agu = Module(new AffineAgu(nTemporalDims, spatialDimSizes, queueDepth));
  agu.io.start := io.start
  agu.io.config := io.config

  // Split full-width read/write ports into data port widths:
  val readVec = Wire(Vec(numPorts, UInt(dataWidth.W)))
  io.read.bits := readVec.asTypeOf(streamerDataType)
  val writeVec = io.write.bits.asTypeOf(Vec(numPorts, UInt(dataWidth.W)))

  val reqQueues = (0 until numPorts).map { i =>
    // Decouple data reqs and tcdm reqs through queues:
    val reqQueue = Module(new Queue(UInt(dataWidth.W), queueDepth))
    reqQueue.io.enq.bits := writeVec(i)

    // Generate requests by combining input data with agu:
    when(io.dir === StreamerDir.write) {
      io.tcdmReqs(i).req.bits.wdata := reqQueue.io.deq.bits
      io.tcdmReqs(i).req.valid := reqQueue.io.deq.valid && agu.io.addrs(i).valid
      reqQueue.io.deq.ready := io.tcdmReqs(i).req.ready && agu.io.addrs(i).valid
      agu.io.addrs(i).ready := io.tcdmReqs(i).req.ready && reqQueue.io.deq.valid
    }.otherwise {
      io.tcdmReqs(i).req.bits.wdata := DontCare
      io.tcdmReqs(i).req.valid := agu.io.addrs(i).valid
      reqQueue.io.deq.ready := false.B
      agu.io.addrs(i).ready := io.tcdmReqs(i).req.ready
    }
    io.tcdmReqs(i).req.bits.addr := agu.io.addrs(i).bits
    io.tcdmReqs(i).req.bits.wen := io.dir === StreamerDir.write;
    io.tcdmReqs(i).req.bits.ben := VecInit(Seq.fill(numPorts)(true.B)).asUInt

    reqQueue
  }

  // Combine many ready/valid into one:
  val allReqReady = reqQueues.map(_.io.enq.ready).reduce(_ && _)
  io.write.ready := allReqReady
  reqQueues.foreach(_.io.enq.valid := io.write.valid && allReqReady)

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
  io.read.valid := allRspValid
  rspQueues.foreach(_.io.deq.ready := io.read.ready && allRspValid)

  // Only signal done when agu is done and all queues are empty
  val allRspEmty = rspQueues.map(_.io.count === 0.U).reduce(_ && _)
  io.done := agu.io.done && allRspEmty
}

package streamer

import chisel3._
import chisel3.util.Queue
import core.DecoupledBusIO
import chisel3.util.{Decoupled, RRArbiter, log2Ceil}
import dataclass.data
import streamer.AguOutput
import core.BusReq
import streamer.StreamerDir.write

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

  // Step 1: Turn result from AGU into read + write requests
  val readReq = agu.io.addrs.bits.isFirst && (io.dir === StreamerDir.read || io.dir === StreamerDir.readWrite);
  val writeReq = agu.io.addrs.bits.isLast && (io.dir === StreamerDir.write || io.dir === StreamerDir.readWrite);
  dontTouch(readReq)
  dontTouch(agu.io)
  dontTouch(writeReq)

  // create separate read / write queues for read reqs and write reqs
  val readQueuesReady, writeQueuesReady = WireInit(false.B)

  // read queues:
  val readReqQueues = (0 until numPorts).map { i =>
    val queue = Module(new Queue(UInt(addrWidth.W), queueDepth))
    queue.io.enq.bits := agu.io.addrs.bits.addrs(i)
    // can enqueue read request if it is valid, if both read and write, also wait for write queues
    queue.io.enq.valid := agu.io.addrs.valid && readReq && readQueuesReady && (!writeReq || writeQueuesReady);
    queue
  }
  readQueuesReady := readReqQueues.map { q => q.io.enq.ready }.reduce(_ && _);

  // write queues:
  val writeReqQueues = (0 until numPorts).map { i =>
    val queue = Module(new Queue(UInt(addrWidth.W), queueDepth))
    queue.io.enq.bits := agu.io.addrs.bits.addrs(i)
    // can enqueue write request if it is valid, if both read and write, also wait for read queues
    queue.io.enq.valid := agu.io.addrs.valid && writeReq && writeQueuesReady && (!readReq || readQueuesReady);
    queue
  }
  writeQueuesReady := writeReqQueues.map { q => q.io.enq.ready }.reduce(_ && _);

  // keep track of the isLast signals to determine coupling with bypass buffer
  val isLastQueue = Module(new Queue(Bool(), 32))
  isLastQueue.io.enq.bits := agu.io.addrs.bits.isLast
  // FIXME: address gen does not wait for isLastQueue, hopefully it is deep enough :')
  isLastQueue.io.enq.valid := agu.io.addrs.fire

  // assign ready signal of agu
  agu.io.addrs.ready := (readQueuesReady || ~readReq) && (writeQueuesReady || ~writeReq)

  // Step 2: Couple write requests with actual write data and put into new queue:
  val writeVec = io.writeData.bits.asTypeOf(Vec(numPorts, UInt(dataWidth.W)))

  // The last write goes into a queue:
  val writeDataQueues = (0 until numPorts).map { i =>
    val queue = Module(
      new Queue(
        new Bundle {
          val data = UInt(dataWidth.W)
          val addr = UInt(addrWidth.W)
        },
        queueDepth
      )
    )
    queue.io.enq.bits.addr := writeReqQueues(i).io.deq.bits
    queue.io.enq.bits.data := writeVec(i)
    queue.io.enq.valid :=
      // We are writing the last element
      isLastQueue.io.deq.bits && isLastQueue.io.deq.valid &&
        // A write address is available
        writeReqQueues(i).io.deq.valid &&
        // Write data is available
        io.writeData.valid

    writeReqQueues(i).io.deq.ready := queue.io.enq.fire
    queue
  }
  val writeDataQueuesReady = writeDataQueues.map { q => q.io.enq.ready }.reduce(_ && _);
  val writeDataQueuesFire = writeDataQueues.map { q => q.io.enq.fire }.reduce(_ && _);

  // Other writes go into the bypass buffer
  val bypassBuffer = Module(new Queue(Vec(numPorts, UInt(dataWidth.W)), 1, pipe = true))
  bypassBuffer.io.enq.bits := writeVec
  bypassBuffer.io.enq.valid :=
    // We are not writing to the last element
    ~isLastQueue.io.deq.bits && isLastQueue.io.deq.valid &&
      // Write data is available
      io.writeData.valid

  // Ready for new data:
  when(isLastQueue.io.deq.valid) {
    when(isLastQueue.io.deq.bits) {
      io.writeData.ready := writeDataQueuesReady
    }.otherwise {
      // In this case, write data to the bypass buffer.
      // Coupling the ready signals creates a combinational loop.
      // However, on writing new data, we are sure the existing element
      // of the buffer will be consumed in a correctly configured system.
      io.writeData.ready := true.B
      // During simulation, assert that this is actually the case.
      assert(bypassBuffer.io.enq.ready)
    }
  }.otherwise { io.writeData.ready := false.B }

  isLastQueue.io.deq.ready := bypassBuffer.io.enq.fire || writeDataQueuesFire

  // Step 3: arbitrate read and write requests to the TCDM

  // signal to check if we can accept new responses
  val roomForRsp = VecInit(Seq.fill(numPorts)(false.B))
  dontTouch(roomForRsp)

  val reqArbiters = (0 until numPorts).map { i =>
    val reqArbiter = Module(new RRArbiter(new BusReq(addrWidth, dataWidth), 2))
    // Attach each arbiters output to the req part of a TCDM port
    io.tcdmReqs(i).req <> reqArbiter.io.out

    // Read requests:
    readReqQueues(i).io.deq.ready := reqArbiter.io.in(0).fire
    reqArbiter.io.in(0).valid := readReqQueues(i).io.deq.valid && roomForRsp(i)
    reqArbiter.io.in(0).bits.addr := readReqQueues(i).io.deq.bits
    reqArbiter.io.in(0).bits.wdata := DontCare
    reqArbiter.io.in(0).bits.wen := false.B;
    reqArbiter.io.in(0).bits.ben := VecInit(Seq.fill(dataWidth / 8)(true.B)).asUInt

    // Write requests:
    writeDataQueues(i).io.deq.ready := reqArbiter.io.in(1).ready
    reqArbiter.io.in(1).valid := writeDataQueues(i).io.deq.valid
    reqArbiter.io.in(1).bits.addr := writeDataQueues(i).io.deq.bits.addr
    reqArbiter.io.in(1).bits.wdata := writeDataQueues(i).io.deq.bits.data
    reqArbiter.io.in(1).bits.wen := true.B;
    reqArbiter.io.in(1).bits.ben := VecInit(Seq.fill(dataWidth / 8)(true.B)).asUInt

    reqArbiter
  }

  // Step 4: collect responses from tcdm

  // only collect read requests
  val readPending = (0 until numPorts).map { i =>
    RegNext(io.tcdmReqs(i).req.fire && ~io.tcdmReqs(i).req.bits.wen)
  }
  val rspQueues = (0 until numPorts).map { i =>
    val rspQueue = Module(new Queue(UInt(dataWidth.W), queueDepth))
    rspQueue.io.enq.bits := io.tcdmReqs(i).rsp.bits.data
    rspQueue.io.enq.valid := io.tcdmReqs(i).rsp.valid && readPending(i)
    // We should always be ready for a tcdm response
    io.tcdmReqs(i).rsp.ready := true.B
    // Check to make sure:
    when(io.tcdmReqs(i).rsp.valid) { assert(io.readData.bits(3) =/= 1.U, "something failed") };
    when(io.tcdmReqs(i).rsp.valid) { assert(io.readData.bits(3) === 1.U, "something else failed") };
    // By default, not ready:
    rspQueue.io.deq.ready := false.B
    // TODO: this is a very conservative bound
    roomForRsp(i) := rspQueue.io.count < (rspQueue.entries.U - 1.U);
    rspQueue
  }
  val allRspQueuesValid = rspQueues.map { q => q.io.deq.valid }.reduce(_ && _);

  // Step 5: send response to the outside
  val readVec = Wire(Vec(numPorts, UInt(dataWidth.W)))
  io.readData.bits := readVec.asTypeOf(streamerDataType)

  bypassBuffer.io.deq.ready := false.B
  when(bypassBuffer.io.deq.valid) {
    readVec := bypassBuffer.io.deq.bits
    bypassBuffer.io.deq.ready := io.readData.ready
    io.readData.valid := true.B
  }.elsewhen(allRspQueuesValid) {
    readVec.zip(rspQueues).map { case (read, resp) =>
      read := resp.io.deq.bits
      resp.io.deq.ready := io.readData.ready
    }
    io.readData.valid := true.B
  }.otherwise {
    readVec := DontCare
    io.readData.valid := false.B
  }

  val allRspEmpty = rspQueues.map(_.io.count === 0.U).reduce(_ && _)
  io.done := agu.io.done && allRspEmpty
}

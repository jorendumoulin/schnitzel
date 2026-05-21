package streamer

import chisel3._
import chisel3.util.Queue
import core.DecoupledBusIO
import chisel3.util.{Decoupled, RRArbiter, log2Ceil}
import dataclass.data
import streamer.{AguOutput, AffineAguConfig}
import core.BusReq
import streamer.StreamerDir.write

object StreamerDir extends ChiselEnum { val read, write, readWrite = Value }

class Streamer(
    affineConfig: AffineAguConfig,
    queueDepth: Int = 2,
    dataWidth: Int = 64
) extends Module {

  val streamerDataType = UInt((affineConfig.numPorts * dataWidth).W)

  val io = IO(new Bundle {
    val start = Input(Bool())
    val config = Input(chiselTypeOf(affineConfig))
    val spatialDimMask = Input(Vec(affineConfig.spatialDimSizes.length, Bool()))
    val tcdmReqs = Vec(affineConfig.numPorts, new DecoupledBusIO(affineConfig.addrWidth, dataWidth))
    val dir = Input(StreamerDir())
    val readData = Decoupled(streamerDataType)
    val writeData = Flipped(Decoupled(streamerDataType))
    val done = Output(Bool())
  })
  dontTouch(io.config)

  val agu = Module(new AffineAgu(affineConfig));
  agu.io.start := io.start
  agu.io.config := io.config

  // Based on the spatial dim mask, compute which 'lanes' of the streamer are enabled.
  // This is achieved by doing it for every dimension separately, and then using kronecker product.
  val maskPerDim = affineConfig.spatialDimSizes.zip(io.spatialDimMask).map { case (s, m) =>
    // creates lists [1, 0, 0, 0, ...] or [1, 1, 1, 1] depending on mask
    true.B +: Vector.fill(s - 1)(m)
  }
  // A 0-D (broadcast) streamer has no spatial dims and therefore no mask bits;
  // `numPorts` collapses to 1 (empty product), so a single always-enabled lane
  // is the correct default — the kronecker reduce below would fail on an empty
  // sequence.
  val laneEnabled: Vec[Bool] =
    if (maskPerDim.isEmpty) VecInit(true.B)
    else
      VecInit(maskPerDim.reduce { (a, b) =>
        for (x <- a; y <- b) yield x && y
      })
  dontTouch(laneEnabled)

  // Step 1: Turn result from AGU into read + write requests
  val readReq = agu.io.addrs.bits.isFirst && (io.dir === StreamerDir.read || io.dir === StreamerDir.readWrite);
  val writeReq = agu.io.addrs.bits.isLast && (io.dir === StreamerDir.write || io.dir === StreamerDir.readWrite);
  dontTouch(readReq)
  dontTouch(agu.io)
  dontTouch(writeReq)

  // create separate read / write queues for read reqs and write reqs
  val readQueuesReady, writeQueuesReady = WireInit(false.B)

  // read queues:
  val readReqQueues = (0 until affineConfig.numPorts).map { i =>
    val queue = Module(new Queue(UInt(affineConfig.addrWidth.W), queueDepth))
    queue.io.enq.bits := agu.io.addrs.bits.addrs(i)
    // can enqueue read request if it is valid, if both read and write, also wait for write queues
    queue.io.enq.valid :=
      agu.io.addrs.valid && readReq && readQueuesReady && (!writeReq || writeQueuesReady) && laneEnabled(i);
    queue
  }
  readQueuesReady := readReqQueues.map { q => q.io.enq.ready }.reduce(_ && _);

  // write queues:
  val writeReqQueues = (0 until affineConfig.numPorts).map { i =>
    val queue = Module(new Queue(UInt(affineConfig.addrWidth.W), queueDepth))
    queue.io.enq.bits := agu.io.addrs.bits.addrs(i)
    // can enqueue write request if it is valid, if both read and write, also wait for read queues
    queue.io.enq.valid :=
      agu.io.addrs.valid && writeReq && writeQueuesReady && (!readReq || readQueuesReady) && laneEnabled(i);
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
  val writeVec = io.writeData.bits.asTypeOf(Vec(affineConfig.numPorts, UInt(dataWidth.W)))

  // The last write goes into a queue:
  val writeDataQueues = (0 until affineConfig.numPorts).map { i =>
    val queue = Module(
      new Queue(
        new Bundle {
          val data = UInt(dataWidth.W)
          val addr = UInt(affineConfig.addrWidth.W)
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
        io.writeData.valid &&
        // Lane is enabled
        laneEnabled(i)

    writeReqQueues(i).io.deq.ready := queue.io.enq.fire
    queue
  }
  val writeDataQueuesReady = writeDataQueues.map { q => q.io.enq.ready }.reduce(_ && _);
  val writeDataQueuesFire =
    writeDataQueues.zipWithIndex.map { case (q, i) => q.io.enq.fire || ~laneEnabled(i) }.reduce(_ && _);

  // Bypass buffer: depth-1 cache that holds a value across multiple consumer
  // reads. Used for both readWrite carry recirculation (writeData fed back as
  // next iteration's read) and stride-0 broadcast reads (one TCDM read whose
  // value must be served on every subsequent cycle until the AGU completes).
  // The enq path is driven below once `rspQueues` exists.
  val bypassBuffer = Module(new Queue(Vec(affineConfig.numPorts, UInt(dataWidth.W)), 1, pipe = true))

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
      when(bypassBuffer.io.enq.valid) {
        assert(bypassBuffer.io.enq.ready, "bypass buffer is not ready for new data!")
      }
    }
  }.otherwise { io.writeData.ready := false.B }

  isLastQueue.io.deq.ready := bypassBuffer.io.enq.fire || writeDataQueuesFire

  // Step 3: arbitrate read and write requests to the TCDM

  // signal to check if we can accept new responses
  val roomForRsp = VecInit(Seq.fill(affineConfig.numPorts)(false.B))
  dontTouch(roomForRsp)

  val reqArbiters = (0 until affineConfig.numPorts).map { i =>
    val reqArbiter = Module(new RRArbiter(new BusReq(affineConfig.addrWidth, dataWidth), 2))
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
  val readPending = (0 until affineConfig.numPorts).map { i =>
    RegNext(io.tcdmReqs(i).req.fire && ~io.tcdmReqs(i).req.bits.wen)
  }
  val rspQueues = (0 until affineConfig.numPorts).map { i =>
    val rspQueue = Module(new Queue(UInt(dataWidth.W), queueDepth))
    rspQueue.io.enq.bits := io.tcdmReqs(i).rsp.bits.data
    rspQueue.io.enq.valid := io.tcdmReqs(i).rsp.valid && readPending(i)
    // We should always be ready for a tcdm response
    io.tcdmReqs(i).rsp.ready := true.B
    // Check to make sure:
    when(io.tcdmReqs(i).rsp.valid) { assert(rspQueue.io.enq.ready, "no room in streamer response buffer") };
    // By default, not ready:
    rspQueue.io.deq.ready := false.B
    // TODO: this is a very conservative bound
    roomForRsp(i) := rspQueue.io.count < (rspQueue.entries.U - 1.U);
    rspQueue
  }
  val allRspQueuesValid = rspQueues.zipWithIndex
    .map { case (q, i) =>
      q.io.deq.valid || ~laneEnabled(i) // ignore disabled lanes
    }
    .reduce(_ && _);

  // Drive bypassBuffer.enq now that rspQueues exists. For read direction the
  // bypass captures the rsp values so they survive past their single drain
  // (stride-0 broadcast). For write/readWrite the existing write-feedback
  // path is preserved.
  bypassBuffer.io.enq.bits := Mux(
    io.dir === StreamerDir.read,
    VecInit(rspQueues.map(_.io.deq.bits)),
    writeVec
  )
  bypassBuffer.io.enq.valid := Mux(
    io.dir === StreamerDir.read,
    allRspQueuesValid,
    ~isLastQueue.io.deq.bits && isLastQueue.io.deq.valid && io.writeData.valid
  )

  // Step 5: send response to the outside
  val readVec = Wire(Vec(affineConfig.numPorts, UInt(dataWidth.W)))
  io.readData.bits := readVec.asTypeOf(streamerDataType)

  bypassBuffer.io.deq.ready := false.B
  when(io.dir === StreamerDir.read && allRspQueuesValid) {
    // Pure read with fresh rsp data — drain rsp directly. Drain the bypass
    // too so its depth-1 slot is free for the parallel enq that snapshots
    // this cycle's value (pipe=true makes that a combinational pass-through).
    readVec.zip(rspQueues).map { case (read, resp) =>
      read := resp.io.deq.bits
      resp.io.deq.ready := io.readData.ready
    }
    bypassBuffer.io.deq.ready := true.B
    io.readData.valid := true.B
  }.elsewhen(bypassBuffer.io.deq.valid) {
    // Cached value: readWrite carry recirculation OR stride-0 broadcast hold.
    // For read direction the cache is held (no drain) so the same value can
    // be served for as long as the AGU iterates.
    readVec := bypassBuffer.io.deq.bits
    bypassBuffer.io.deq.ready :=
      Mux(io.dir === StreamerDir.read, false.B, io.readData.ready)
    io.readData.valid := true.B
  }.elsewhen(allRspQueuesValid) {
    // Write/readWrite fallback when bypass is empty.
    readVec.zip(rspQueues).map { case (read, resp) =>
      read := resp.io.deq.bits
      resp.io.deq.ready := io.readData.ready
    }
    io.readData.valid := true.B
  }.otherwise {
    readVec := DontCare
    io.readData.valid := false.B
  }

  val allQueuesEmpty =
    rspQueues.map(_.io.count === 0.U).reduce(_ && _) &&
      writeDataQueues.map(_.io.count === 0.U).reduce(_ && _) &&
      readReqQueues.map(_.io.count === 0.U).reduce(_ && _) &&
      writeReqQueues.map(_.io.count === 0.U).reduce(_ && _)
  io.done := agu.io.done && allQueuesEmpty

  def getConfig = Map(
    "access_width" -> ujson.Num(dataWidth)
  ) ++ affineConfig.getConfig
}

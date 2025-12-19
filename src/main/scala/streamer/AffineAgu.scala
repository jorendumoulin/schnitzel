package streamer

import chisel3._
import chisel3.util.{Decoupled, Queue}

class AffineAguConfig(val nTemporalDims: Int, val spatialDimSizes: Seq[Int]) extends Bundle {
  val baseAddr = UInt(32.W)
  val temporalStrides = Vec(nTemporalDims, UInt(32.W))
  val temporalBounds = Vec(nTemporalDims, UInt(32.W))
  val spatialStrides = Vec(spatialDimSizes.length, UInt(32.W))
}

class AffineAgu(
    nTemporalDims: Int,
    spatialDimSizes: Seq[Int],
    queueDepth: Int = 2
) extends Module {
  // Calculate total number of spatial outputs
  val numSpatialOutputs = spatialDimSizes.fold(1)(_ * _)

  val io = IO(new Bundle {
    // Control signals
    val start = Input(Bool())

    // Configuration inputs
    val config = Input(new AffineAguConfig(nTemporalDims, spatialDimSizes))

    // Address outputs (decoupled with queues)
    val addrs = Vec(numSpatialOutputs, Decoupled(UInt(32.W)))

    // Status output
    val done = Output(Bool())
  })

  // State definitions
  object State extends ChiselEnum { val idle, busy = Value; }
  val state = RegInit(State.idle)
  // Go to busy state on start signal
  when(state === State.idle && io.start) { state := State.busy; }

  // Counter registers for each temporal dimension
  val temporalCounters = RegInit(VecInit(Seq.fill(nTemporalDims)(0.U(32.W))))

  // Calculate the result of the temporal address
  val temporalAddress = io.config.baseAddr + temporalCounters
    .zip(io.config.temporalStrides)
    .map { case (counter, stride) => counter * stride }
    .reduce(_ + _)

  // Calculate final addresses by applying spatial strides
  val addresses = VecInit(
    for (outputIdx <- 0 until numSpatialOutputs) yield {
      var addrOffset = 0.U(32.W)
      var multiplier = 1.U(32.W)

      for (dim <- spatialDimSizes.indices) {
        val dimSize = spatialDimSizes(dim)
        val dimIndex = (outputIdx.U / multiplier) % dimSize.U
        addrOffset = addrOffset + (dimIndex * io.config.spatialStrides(dim))
        multiplier = multiplier * dimSize.U
      }

      temporalAddress + addrOffset
    }
  )

  // Pass outputs to queues for fine-grained prefetching
  val queues = Seq.fill(numSpatialOutputs)(Module(new Queue(UInt(32.W), queueDepth)))
  queues.zip(addresses).foreach { case (queue, address) => queue.io.enq.bits := address }
  queues.zip(io.addrs).foreach { case (queue, output) => queue.io.deq <> output }
  // Push new address to address queues if all queues can accept new data:
  val queues_ready = queues.map(_.io.enq.ready).reduce(_ | _)
  val enqueue = queues_ready && state === State.busy
  queues.foreach(_.io.enq.valid := enqueue)

  // Remaining control logic:
  val allDone = io.config.temporalBounds
    .zip(temporalCounters)
    .map { case (bound, counter) => counter === (bound - 1.U) }
    .reduce(_ | _);

  when(enqueue && allDone) { state := State.idle; }
  when(enqueue) { incrementCounters(); }

  // Function to increment counters in nested loop fashion
  def incrementCounters(): Unit = {
    // Carry propagation: start with innermost dimension (index 0)
    var carry = true.B
    for (i <- 0 until nTemporalDims) {
      when(carry) {
        when(temporalCounters(i) === io.config.temporalBounds(i) - 1.U) {
          temporalCounters(i) := 0.U
          // Carry continues to next dimension
        }.otherwise {
          temporalCounters(i) := temporalCounters(i) + 1.U
          carry = false.B
        }
      }
    }
  }

  // Done signal
  io.done := state === State.idle;
}

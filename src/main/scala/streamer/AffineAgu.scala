package streamer

import chisel3._
import chisel3.util.{Decoupled, Queue}
import chisel3.util.Counter

/** Configuration parameters for the Affine Address Generation Unit (AGU). * Defines the iteration space and memory
  * layout for both temporal (time-multiplexed) and spatial (parallel) address calculations.
  * @param nTemporalDims
  *   Number of nested loops for temporal address generation.
  * @param spatialDimSizes
  *   A sequence representing the sizes of each spatial dimension.
  */
class AffineAguConfig(val nTemporalDims: Int, val spatialDimSizes: Seq[Int]) extends Bundle {

  /** The starting memory address for the affine sequence. */
  val baseAddr = UInt(32.W)

  /** The step size for each temporal dimension. */
  val temporalStrides = Vec(nTemporalDims, UInt(32.W))

  /** The loop bounds (maximum iterations) for each temporal dimension. */
  val temporalBounds = Vec(nTemporalDims, UInt(32.W))

  /** The step size for each spatial dimension in the output vector. */
  val spatialStrides = Vec(spatialDimSizes.length, UInt(32.W))

  /** Calculates the total number of 32-bit words required for this config. Useful for memory-mapping and CSR offset
    * calculations.
    */
  def numRegs: Int = {
    1 + (nTemporalDims * 2) + spatialDimSizes.length
  }
}

/** Affine Address Generation Unit (AGU). This module generates a stream of addresses based on nested loop parameters.
  * It combines a temporal iteration (looping over time) with a spatial expansion (generating multiple parallel
  * addresses per cycle).
  * @param nTemporalDims
  *   Number of nested loops to iterate through.
  * @param spatialDimSizes
  *   Dimensions of the spatial hardware array (e.g., Seq(4, 4) for a 16-lane output).
  * @param queueDepth
  *   The depth of the internal Decoupled queues for each address output.
  */
class AffineAgu(
    nTemporalDims: Int,
    spatialDimSizes: Seq[Int],
    queueDepth: Int = 2
) extends Module {

  /** Total number of parallel address outputs calculated as the product of all spatial dimensions. */
  val numSpatialOutputs = spatialDimSizes.fold(1)(_ * _)

  val io = IO(new Bundle {

    /** Pulse high to begin address generation. */
    val start = Input(Bool())

    /** Runtime configuration for strides, bounds, and base address. */
    val config = Input(new AffineAguConfig(nTemporalDims, spatialDimSizes))

    /** Vector of Decoupled interfaces providing calculated addresses. */
    val addrs = Vec(numSpatialOutputs, Decoupled(UInt(32.W)))

    /** High when the AGU is idle and has finished its current iteration bounds. */
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
  val queues = Seq.fill(numSpatialOutputs)(Module(new Queue(UInt(32.W), 10)))
  queues.foreach { q =>
    dontTouch(q.io.enq)
    dontTouch(q.io.deq)
    dontTouch(q.io.count)
    dontTouch(q.do_deq)
    dontTouch(q.do_enq)
  }
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

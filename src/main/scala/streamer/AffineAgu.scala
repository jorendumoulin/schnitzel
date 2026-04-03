package streamer

import chisel3._
import chisel3.util.{Decoupled}

/** Configuration parameters for the Affine Address Generation Unit (AGU). * Defines the iteration space and memory
  * layout for both temporal (time-multiplexed) and spatial (parallel) address calculations.
  * @param nTemporalDims
  *   Number of nested loops for temporal address generation.
  * @param spatialDimSizes
  *   A sequence representing the sizes of each spatial dimension.
  * @param addressWidth
  *   bitwidth of addresses.
  */
class AffineAguConfig(val nTemporalDims: Int, val spatialDimSizes: Seq[Int], val addressWidth: Int = 32)
    extends Bundle {

  /** The starting memory address for the affine sequence. */
  val baseAddr = UInt(addressWidth.W)

  /** The step size for each temporal dimension. */
  val temporalStrides = Vec(nTemporalDims, UInt(addressWidth.W))

  /** The loop bounds (maximum iterations) for each temporal dimension. */
  val temporalBounds = Vec(nTemporalDims, UInt(addressWidth.W))

  /** The step size for each spatial dimension in the output vector. */
  val spatialStrides = Vec(spatialDimSizes.length, UInt(addressWidth.W))

  /** Calculates the total number of 32-bit words required for this config. Useful for memory-mapping and CSR offset
    * calculations.
    */
  def numRegs: Int = {
    1 + (nTemporalDims * 2) + spatialDimSizes.length
  }
}

class AguOutput(val addressWidth: Int, val numSpatialOutputs: Int) extends Bundle {
  val addrs = Vec(numSpatialOutputs, UInt(addressWidth.W))
  val isFirst = Bool()
  val isLast = Bool()
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
    queueDepth: Int = 2,
    addressWidth: Int = 32
) extends Module {

  /** Total number of parallel address outputs calculated as the product of all spatial dimensions. */
  val numSpatialOutputs = spatialDimSizes.fold(1)(_ * _)

  val io = IO(new Bundle {

    /** Pulse high to begin address generation. */
    val start = Input(Bool())

    /** Runtime configuration for strides, bounds, and base address. */
    val config = Input(new AffineAguConfig(nTemporalDims, spatialDimSizes, addressWidth))

    /** Vector of Decoupled interfaces providing calculated addresses. */
    val addrs = Decoupled(new AguOutput(addressWidth, numSpatialOutputs))

    /** High when the AGU is idle and has finished its current iteration bounds. */
    val done = Output(Bool())
  })

  // State definitions
  object State extends ChiselEnum { val idle, busy = Value; }
  val state = RegInit(State.idle)
  // Go to busy state on start signal
  when(state === State.idle && io.start) { state := State.busy; }

  // Counter registers for each temporal dimension
  val temporalCounters = RegInit(VecInit(Seq.fill(nTemporalDims)(0.U(addressWidth.W))))

  // Calculate the result of the temporal address
  val temporalAddress = io.config.baseAddr + temporalCounters
    .zip(io.config.temporalStrides)
    .map { case (counter, stride) => counter * stride }
    .reduce(_ + _)

  // Calculate final addresses by applying spatial strides
  val addresses = VecInit(
    for (outputIdx <- 0 until numSpatialOutputs) yield {
      var addrOffset = 0.U(addressWidth.W)
      var multiplier = 1.U(addressWidth.W)

      for (dim <- spatialDimSizes.indices) {
        val dimSize = spatialDimSizes(dim)
        val dimIndex = (outputIdx.U / multiplier) % dimSize.U
        addrOffset = addrOffset + (dimIndex * io.config.spatialStrides(dim))
        multiplier = multiplier * dimSize.U
      }

      temporalAddress + addrOffset
    }
  )

  // Advance when all consumers are ready
  val advance = io.addrs.ready && state === State.busy

  // Address generation is done when all bounds have hit their limit
  val allDone = io.config.temporalBounds
    .zip(temporalCounters)
    .map { case (bound, counter) =>
      (bound <= 1.U) || counter === (bound - 1.U)
    }
    .reduce(_ && _);

  // High when not performing a reduction: All strides are larger than 0
  // When performing a temporal reduction, only high for first element
  // Not affected by dimensions with bound <= 1
  val globalIsFirst = io.config.temporalStrides
    .zip(io.config.temporalBounds)
    .zip(temporalCounters)
    .map { case ((stride, bound), count) =>
      (bound <= 1.U) || (stride =/= 0.U) || (count === 0.U)
    }
    .reduce(_ && _)

  // High when not performing a reduction: All strides are larger than 0
  // When performing a temporal reduction, only high for last element
  // Not affected by dimensions with bound <= 1
  val globalIsLast = io.config.temporalStrides
    .zip(io.config.temporalBounds)
    .zip(temporalCounters)
    .map { case ((stride, bound), count) =>
      (bound <= 1.U) || (stride =/= 0.U) || (count === bound - 1.U)
    }
    .reduce(_ && _)

  io.addrs.valid := state === State.busy
  io.addrs.bits.addrs := addresses
  io.addrs.bits.isFirst := globalIsFirst
  io.addrs.bits.isLast := globalIsLast

  when(advance && allDone) { state := State.idle; }
  when(advance) { incrementCounters(); }

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

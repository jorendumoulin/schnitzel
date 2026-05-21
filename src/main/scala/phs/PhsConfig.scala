package phs

import upickle.default.{ReadWriter => RW, macroRW}

// --- PHS Streamer Config ---

case class PhsStreamerConfig(
    streamType: String, // "read", "write", or "readWrite"
    nTemporalDims: Int,
    spatialDimSizes: Seq[Int],
    // Only meaningful for `readWrite`. true (default) when the BlackBox actually
    // consumes the carry-input data (data_K_*). When false the streamer still
    // performs both reads and writes (e.g., to keep address pacing) but its
    // readData.valid does NOT gate other writers' writeData.valid in the
    // accelerator wiring — preventing a deadlock when the BB doesn't depend
    // on the carry value. Pure `read`/`write` streamers ignore this field.
    carryUsed: Boolean = true
) {
  def numTcdmPorts: Int = spatialDimSizes.product
  def numCsrRegs: Int = 1 + nTemporalDims * 2 + spatialDimSizes.length
}
object PhsStreamerConfig { implicit val rw: RW[PhsStreamerConfig] = macroRW }

// --- PHS Accelerator Config ---

case class PhsAcceleratorConfig(
    streamers: Seq[PhsStreamerConfig],
    numSwitches: Int,
    switchBitwidths: Seq[Int] = Seq(),
    maskBitwidths: Seq[Int] = Seq(),
    moduleName: String = "",
    svPath: String = ""
) {
  def totalTcdmPorts: Int = streamers.map(_.numTcdmPorts).sum
  def numCsrRegs: Int = streamers.map(_.numCsrRegs).sum + numSwitches

  /** Get bitwidth for switch i. Falls back to 32 (full CSR width) if not specified. */
  def switchBitwidth(i: Int): Int =
    if (i < switchBitwidths.length) switchBitwidths(i) else 32

  /** Per-streamer enable mask bitwidth. Indexed by position in `streamers`.
    * Falls back to the streamer's number of spatial dimensions (min 1) —
    * one enable bit per dim. */
  def maskBitwidth(i: Int): Int =
    if (i < maskBitwidths.length) maskBitwidths(i)
    else math.max(1, streamers(i).spatialDimSizes.length)

  // A readWrite streamer participates as both a reader and a writer.
  def readStreamers: Seq[PhsStreamerConfig] =
    streamers.filter(s => s.streamType == "read" || s.streamType == "readWrite")
  def writeStreamers: Seq[PhsStreamerConfig] =
    streamers.filter(s => s.streamType == "write" || s.streamType == "readWrite")
}
object PhsAcceleratorConfig {
  implicit val rw: RW[PhsAcceleratorConfig] = macroRW

  /** Default config matching the existing ALU accelerator: 2 read + 1 write streamer, 1 switch */
  val defaultAlu = PhsAcceleratorConfig(
    streamers = Seq(
      PhsStreamerConfig("read", 1, Seq(4)),
      PhsStreamerConfig("read", 1, Seq(4)),
      PhsStreamerConfig("write", 1, Seq(4))
    ),
    numSwitches = 1,
    switchBitwidths = Seq(2),
    maskBitwidths = Seq(1, 1, 1),
    moduleName = "acc1_array",
    svPath = "src/main/resources/phs/acc1_array.sv"
  )
}

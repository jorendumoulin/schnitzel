package phs

import chisel3._
import chisel3.util.HasBlackBoxPath
import core.DecoupledBusIO
import streamer.{Streamer, AffineAguConfig, StreamerDir}
import csr.CsrIO
import csr.CsrInterface

/** BlackBox wrapper for PHS-generated SystemVerilog datapath.
  *
  * Port naming matches the PHS compiler output convention:
  *   - data_{readerIdx}_{elementIdx} : input  [dataWidth-1:0]
  *   - switch_{idx}                  : input  [bitwidth-1:0]
  *   - out_{writerIdx}_{elementIdx}  : output [dataWidth-1:0]
  *   - mask_{streamerIdx}            : output [maskBitwidth-1:0]
  *
  * Each mask is per physical streamer: one bit per spatial dimension (min 1 bit). Bit k enables spatial dim k; when
  * cleared, that dim collapses to size 1 so the streamer only issues TCDM requests for its "dimIndex == 0"
  * representative lane. Drives the streamer's `spatialDimMask` directly.
  */
class PhsDatapathBlackBox(config: PhsAcceleratorConfig, dataWidth: Int) extends BlackBox with HasBlackBoxPath {

  override val desiredName = config.moduleName

  val readConfigs = config.readStreamers
  val writeConfigs = config.writeStreamers

  // Build flat port Record matching PHS verilog naming convention
  val io = IO(new Record {
    val elements = {
      val ports = collection.mutable.LinkedHashMap[String, Data]()

      // Read data inputs: data_{readerIdx}_{elementIdx}
      for ((sc, rIdx) <- readConfigs.zipWithIndex) {
        val numElements = sc.spatialDimSizes.product
        for (eIdx <- 0 until numElements) {
          ports += s"data_${rIdx}_${eIdx}" -> Input(UInt(dataWidth.W))
        }
      }

      // Switch inputs: switch_{idx}
      for (i <- 0 until config.numSwitches) {
        ports += s"switch_${i}" -> Input(UInt(config.switchBitwidth(i).W))
      }

      // Write data outputs: out_{writerIdx}_{elementIdx}
      for ((sc, wIdx) <- writeConfigs.zipWithIndex) {
        val numElements = sc.spatialDimSizes.product
        for (eIdx <- 0 until numElements) {
          ports += s"out_${wIdx}_${eIdx}" -> Output(UInt(dataWidth.W))
        }
      }

      // Per-streamer mask outputs: mask_{streamerIdx} (indexed by position in
      // `config.streamers`, one mask per physical streamer regardless of role).
      for (sIdx <- config.streamers.indices) {
        ports += s"mask_${sIdx}" -> Output(UInt(config.maskBitwidth(sIdx).W))
      }

      collection.immutable.SeqMap.from(ports)
    }
  })

  addPath(config.svPath)
}

/** Generic PHS accelerator parameterized by PhsAcceleratorConfig.
  *
  * The datapath is an external PHS-generated SystemVerilog BlackBox module.
  *
  * CSR base address is 0 — PhsCsrDemux handles address routing and rebasing, so software still writes to the same
  * absolute addresses.
  */
class PhsAccelerator(addrWidth: Int, dataWidth: Int, config: PhsAcceleratorConfig, csrBase: Int = 0x900)
    extends Module {

  val totalPorts = config.totalTcdmPorts

  val io = IO(new Bundle {
    val tcdmPorts = Vec(totalPorts, new DecoupledBusIO(addrWidth, dataWidth))
    val csr = Flipped(new CsrIO)
  })

  // ---- CSR Interface ----
  val csrItf = Module(new CsrInterface(config.numCsrRegs, csrBase))
  csrItf.io.csr <> io.csr

  // ---- Create streamers from config ----
  val queueDepth = 3
  var csrOffset = 0
  var tcdmPortIdx = 0

  val streamers = config.streamers.map { sc =>
    val s = Module(new Streamer(sc.nTemporalDims, sc.spatialDimSizes, queueDepth, addrWidth, dataWidth))
    val numPorts = sc.numTcdmPorts
    val numRegs = sc.numCsrRegs

    // Wire TCDM ports
    for (j <- 0 until numPorts) {
      s.io.tcdmReqs(j) <> io.tcdmPorts(tcdmPortIdx)
      tcdmPortIdx += 1
    }

    // Wire CSR config: take registers [csrOffset..csrOffset+numRegs), reverse
    // for correct bit mapping (register 0 -> baseAddr at MSB), then reinterpret
    // as AffineAguConfig bundle. This matches the pattern in AluAccelerator.
    val regs = (0 until numRegs).map(j => csrItf.io.vals(csrOffset + j))
    s.io.config := VecInit(regs.reverse).asTypeOf(new AffineAguConfig(sc.nTemporalDims, sc.spatialDimSizes))
    // spatialDimMask is wired below for write streamers (from the blackbox).
    // Default to all-enabled here; read streamers keep this value.
    s.io.spatialDimMask := VecInit(Seq.fill(sc.spatialDimSizes.length)(true.B))
    csrOffset += numRegs

    // Wire start and direction
    s.io.start := csrItf.io.start
    s.io.dir := (sc.streamType match {
      case "read"      => StreamerDir.read
      case "write"     => StreamerDir.write
      case "readWrite" => StreamerDir.readWrite
      case other       => throw new IllegalArgumentException(s"Unknown streamType: $other")
    })

    // Tie off unused data port. readWrite uses both sides, so nothing is tied.
    sc.streamType match {
      case "read"  => s.io.writeData := DontCare
      case "write" => s.io.readData := DontCare
      case _       => // readWrite: both sides are wired below
    }

    s
  }

  // ---- Switch values from CSR ----
  val switches = (0 until config.numSwitches).map(i => csrItf.io.vals(csrOffset + i))

  // ---- Separate read and write streamers ----
  // A readWrite streamer participates in both sides: its read path provides
  // data_{rIdx}_* to the blackbox, its write path consumes out_{wIdx}_*.
  val readStreamers =
    streamers.zip(config.streamers).filter { case (_, c) => c.streamType == "read" || c.streamType == "readWrite" }.map(_._1)
  val readStreamerConfigs =
    config.streamers.filter(c => c.streamType == "read" || c.streamType == "readWrite")
  val writeStreamers =
    streamers.zip(config.streamers).filter { case (_, c) => c.streamType == "write" || c.streamType == "readWrite" }.map(_._1)

  // ---- Datapath (PHS-generated SystemVerilog BlackBox) ----
  val bb = Module(new PhsDatapathBlackBox(config, dataWidth))
  val readConfigs = config.readStreamers
  val writeConfigs = config.writeStreamers

  // Wire read streamer data -> BlackBox data inputs
  for ((sc, rIdx) <- readConfigs.zipWithIndex) {
    val numElements = sc.spatialDimSizes.product
    val bits = readStreamers(rIdx).io.readData.bits.asTypeOf(Vec(numElements, UInt(dataWidth.W)))
    for (eIdx <- 0 until numElements) {
      bb.io.elements(s"data_${rIdx}_${eIdx}") := bits(eIdx)
    }
  }

  // Wire switches -> BlackBox switch inputs
  for (i <- 0 until config.numSwitches) {
    bb.io.elements(s"switch_${i}") := switches(i)(config.switchBitwidth(i) - 1, 0)
  }

  // For each reader, gate its `readData.valid` contribution to the AND that
  // drives writers' `writeData.valid`. Pure readers always contribute. A
  // readWrite streamer contributes only when its `carryUsed` flag is true:
  // when the BlackBox doesn't actually consume `data_K_*`, requiring its
  // valid would deadlock the handshake (the write would never fire because
  // the carry-side read never advances).
  val readDataValidContrib = readStreamers.zip(readStreamerConfigs).map { case (s, c) =>
    if (c.streamType == "readWrite" && !c.carryUsed) true.B
    else s.io.readData.valid
  }
  val combinedReadDataValid =
    if (readDataValidContrib.isEmpty) true.B else readDataValidContrib.reduce(_ && _)

  // Wire BlackBox outputs -> write streamer data
  for ((sc, wIdx) <- writeConfigs.zipWithIndex) {
    val numElements = sc.spatialDimSizes.product
    val outBits = Wire(Vec(numElements, UInt(dataWidth.W)))
    for (eIdx <- 0 until numElements) {
      outBits(eIdx) := bb.io.elements(s"out_${wIdx}_${eIdx}")
    }
    writeStreamers(wIdx).io.writeData.bits := outBits.asTypeOf(UInt((dataWidth * numElements).W))
    writeStreamers(wIdx).io.writeData.valid := combinedReadDataValid
  }

  // Per-streamer spatial dimension masks: bit k of the blackbox's mask output
  // enables spatial dim k of the corresponding streamer. When a bit is 0, that
  // spatial dim collapses to size 1, suppressing TCDM requests for lanes that
  // only differ along that dim. One mask per physical streamer.
  for ((sc, sIdx) <- config.streamers.zipWithIndex) {
    val maskBits = bb.io.elements(s"mask_${sIdx}").asUInt
    val numDims = sc.spatialDimSizes.length
    val dimMask = VecInit((0 until numDims).map(k => maskBits(k)))
    streamers(sIdx).io.spatialDimMask := dimMask
  }

  // BlackBox is purely combinational — read streamers are ready when writes are ready
  for (rIdx <- readStreamers.indices) {
    readStreamers(rIdx).io.readData.ready := writeStreamers.map(_.io.writeData.ready).reduce(_ && _)
  }

  // Done when all write streamers complete
  csrItf.io.done := writeStreamers.map(_.io.done).reduce(_ && _)
}

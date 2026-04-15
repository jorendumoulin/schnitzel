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
  *   - data_{readerIdx}_{elementIdx} : input [dataWidth-1:0]
  *   - switch_{idx} : input [bitwidth-1:0]
  *   - out_{writerIdx}_{elementIdx} : output [dataWidth-1:0]
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
    csrOffset += numRegs

    // Wire start and direction
    s.io.start := csrItf.io.start
    s.io.dir := (if (sc.streamType == "read") StreamerDir.read else StreamerDir.write)

    // Tie off unused data port
    if (sc.streamType == "read") {
      s.io.writeData := DontCare
    } else {
      s.io.readData := DontCare
    }

    s
  }

  // ---- Switch values from CSR ----
  val switches = (0 until config.numSwitches).map(i => csrItf.io.vals(csrOffset + i))

  // ---- Separate read and write streamers ----
  val readStreamers = streamers.zip(config.streamers).filter(_._2.streamType == "read").map(_._1)
  val writeStreamers = streamers.zip(config.streamers).filter(_._2.streamType == "write").map(_._1)

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

  // Wire BlackBox outputs -> write streamer data
  for ((sc, wIdx) <- writeConfigs.zipWithIndex) {
    val numElements = sc.spatialDimSizes.product
    val outBits = Wire(Vec(numElements, UInt(dataWidth.W)))
    for (eIdx <- 0 until numElements) {
      outBits(eIdx) := bb.io.elements(s"out_${wIdx}_${eIdx}")
    }
    writeStreamers(wIdx).io.writeData.bits := outBits.asTypeOf(UInt((dataWidth * numElements).W))
    writeStreamers(wIdx).io.writeData.valid := readStreamers.map(_.io.readData.valid).reduce(_ && _)
  }

  // BlackBox is purely combinational — read streamers are ready when writes are ready
  for (rIdx <- readStreamers.indices) {
    readStreamers(rIdx).io.readData.ready := writeStreamers.map(_.io.writeData.ready).reduce(_ && _)
  }

  // Done when all write streamers complete
  csrItf.io.done := writeStreamers.map(_.io.done).reduce(_ && _)
}

package core

import chisel3._
import chisel3.util.{HasBlackBoxResource, Decoupled}
import java.nio.file.{Files, Paths}
import axi.AXIBundle
import axi.AXIConfig

import chisel3._
import circt.stage.ChiselStage

class DebugDmiReq extends Bundle {
  val addr = UInt(7.W)
  val data = UInt(32.W)
  val op = UInt(2.W)
}

class DebugDmiRsp extends Bundle {
  val data = UInt(32.W)
  val resp = UInt(2.W)
}

class DebugDmi extends Bundle {
  val req = Decoupled(new DebugDmiReq)
  val resp = Flipped(Decoupled(new DebugDmiRsp))
}

class SnaxSystem extends BlackBox with HasBlackBoxResource {

  val io = IO(new Bundle {
    val io_aggregator_5_clock = Input(Clock())
    val io_aggregator_5_reset = Input(Bool())
    val io_aggregator_4_clock = Input(Clock())
    val io_aggregator_4_reset = Input(Bool())
    val io_aggregator_3_clock = Input(Clock())
    val io_aggregator_3_reset = Input(Bool())
    val io_aggregator_2_clock = Input(Clock())
    val io_aggregator_2_reset = Input(Bool())
    val io_aggregator_1_clock = Input(Clock())
    val io_aggregator_1_reset = Input(Bool())
    val io_aggregator_0_clock = Input(Clock())
    val io_aggregator_0_reset = Input(Bool())
    val resetctrl_hartIsInReset_0 = Input(Bool())
    val debug_clock = Input(Clock())
    val debug_reset = Input(Bool())
    val debug_ndreset = Output(Bool())
    val debug_dmactive = Output(Bool())
    val debug_dmactiveAck = Input(Bool())
    val debug_clockeddmi_dmiClock = Input(Clock())
    val debug_clockeddmi_dmiReset = Input(Bool())

    val debug_clockeddmi_dmi = Flipped(new DebugDmi)

    val mem_axi4_0 = new AXIBundle(new AXIConfig(userWidth = 0, regionWidth = 0));

  })

  // Add ibex resources:
  addResource("/rocket/rocket.sv")

}

class BigCore extends Module {
  val io = IO(new Bundle { val axi = new AXIBundle(new AXIConfig) })
  val rocket = Module(new SnaxSystem)
  rocket.io := DontCare
  rocket.io.mem_axi4_0 <> io.axi

  rocket.io.debug_clock := clock
  rocket.io.debug_reset := reset.asBool
  rocket.io.io_aggregator_0_clock := clock
  rocket.io.io_aggregator_1_clock := clock
  rocket.io.io_aggregator_2_clock := clock
  rocket.io.io_aggregator_3_clock := clock
  rocket.io.io_aggregator_4_clock := clock
  rocket.io.io_aggregator_5_clock := clock
  rocket.io.io_aggregator_0_reset := reset.asBool
  rocket.io.io_aggregator_1_reset := reset.asBool
  rocket.io.io_aggregator_2_reset := reset.asBool
  rocket.io.io_aggregator_3_reset := reset.asBool
  rocket.io.io_aggregator_4_reset := reset.asBool
  rocket.io.io_aggregator_5_reset := reset.asBool

}

// object EmitVerilog extends App {

//   // Generate Verilog to the generated/ directory
//   val outputDir = "generated"

//   ChiselStage.emitSystemVerilogFile(
//     new BigCore,
//     args = Array("--target-dir", outputDir),
//     firtoolOpts = Array(
//       "-disable-all-randomization",
//       "-strip-debug-info"
//     )
//   )

// }

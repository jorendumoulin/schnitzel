package sim

import chisel3._
import circt.stage.ChiselStage
import top.Top

/** Elaboration object to generate Verilog for spitchel integration
  *
  * This generates the Verilog RTL that will be verilated and integrated with the spike/fesvr infrastructure.
  */
object EmitVerilog extends App {

  println("Generating Verilog for Schnitzel Core...")

  // Generate Verilog to the generated/ directory
  val outputDir = "generated"

  ChiselStage.emitSystemVerilogFile(
    new Top,
    args = Array("--target-dir", outputDir),
    firtoolOpts = Array(
      "-disable-all-randomization",
      "-strip-debug-info"
    )
  )

  println(s"Verilog generated in $outputDir/Top.sv")
}

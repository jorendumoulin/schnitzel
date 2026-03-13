package sim

import chisel3._
import circt.stage.ChiselStage
import top.Top
import upickle.default.write
import java.io.File
import java.io.PrintWriter

/** Elaboration object to generate Verilog for spitchel integration
  *
  * This generates the Verilog RTL that will be verilated and integrated with the spike/fesvr infrastructure.
  */
object EmitVerilog extends App {

  println("Generating Verilog for Schnitzel Core...")

  // Generate Verilog to the generated/ directory
  val outputDir = "generated"

  var topModule: Top = null

  ChiselStage.emitSystemVerilogFile(
    {
      topModule = new Top
      topModule
    },
    args = Array("--target-dir", outputDir),
    firtoolOpts = Array(
      "-disable-all-randomization",
      "-strip-debug-info"
    )
  )
  val configJson = write(topModule.getConfig, indent = 2)

  val dir = new File(outputDir)

  val pw = new PrintWriter(new File(s"$outputDir/config.json"))
  try {
    pw.write(configJson)
    println(s"Successfully generated metadata at $outputDir/config.json")
  } finally {
    pw.close()
  }

  println(s"Verilog generated in $outputDir/Top.sv")
}

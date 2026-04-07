package sim

import chisel3._
import circt.stage.ChiselStage
import top.Top
import upickle.default.{write, read}
import java.io.File
import java.io.PrintWriter
import config.PhsAcceleratorConfig

/** Elaboration object to generate Verilog for schnitzel integration.
  *
  * Set PHS_CONFIG env var to a JSON file path to override accelerator config.
  * The JSON should be a Seq[Seq[PhsAcceleratorConfig]] (per-core list).
  * If not set, defaults to the standard ALU accelerator on core 1.
  */
object EmitVerilog extends App {

  println("Generating Verilog for Schnitzel Core...")

  // Load PHS config from environment or use default
  val phsConfigs = sys.env.get("PHS_CONFIG") match {
    case Some(path) =>
      println(s"Loading PHS config from $path")
      val json = scala.io.Source.fromFile(path).mkString
      read[Seq[Seq[PhsAcceleratorConfig]]](json)
    case None =>
      Seq(Seq[PhsAcceleratorConfig](), Seq(PhsAcceleratorConfig.defaultAlu))
  }

  val outputDir = "generated"

  var topModule: Top = null

  ChiselStage.emitSystemVerilogFile(
    {
      topModule = new Top(phsConfigs)
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

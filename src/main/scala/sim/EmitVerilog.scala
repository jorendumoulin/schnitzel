package sim

import chisel3._
import circt.stage.ChiselStage
import top.{Top, PhsTop}
import upickle.default.{write, read}
import java.io.File
import java.io.PrintWriter
import config.PhsAcceleratorConfig

/** Elaboration object to generate Verilog for schnitzel.
  *
  * Set PHS_CONFIG env var to a JSON file path to override accelerator config. The JSON should be a
  * Seq[Seq[PhsAcceleratorConfig]] (per-core list). If not set, uses the default Top with AluAccelerator.
  */
object EmitVerilog extends App {

  println("Generating Verilog for Schnitzel Core...")

  val outputDir = "generated"

  // Load PHS config from environment if set
  val phsConfigs = sys.env.get("PHS_CONFIG").map { path =>
    println(s"Loading PHS config from $path")
    val json = scala.io.Source.fromFile(path).mkString
    read[Seq[Seq[PhsAcceleratorConfig]]](json)
  }

  var topModule: Top = null

  ChiselStage.emitSystemVerilogFile(
    {
      topModule = phsConfigs match {
        case Some(configs) => new PhsTop(configs)
        case None          => new Top
      }
      topModule
    },
    args = Array("--target-dir", outputDir),
    firtoolOpts = Array(
      "-disable-all-randomization",
      "-strip-debug-info"
    )
  )

  val configJson = write(topModule.getConfig, indent = 2)
  val pw = new PrintWriter(new File(s"$outputDir/config.json"))
  try {
    pw.write(configJson)
    println(s"Successfully generated metadata at $outputDir/config.json")
  } finally {
    pw.close()
  }

  println(s"Verilog generated in $outputDir/Top.sv")
}

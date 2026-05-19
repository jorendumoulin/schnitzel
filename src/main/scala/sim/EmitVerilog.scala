package sim

import chisel3._
import circt.stage.ChiselStage
import top.{Top, TensorTop}
import config.SystemConfig
import upickle.default.write
import java.io.File
import java.io.PrintWriter

/** Elaboration object to generate Verilog for spitchel integration
  *
  * This generates the Verilog RTL that will be verilated and integrated with the spike/fesvr infrastructure.
  *
  * Pass `--top=<name>` to select which top-level module to elaborate. Extend the match below to add new
  * configurations.
  */
object EmitVerilog extends App {

  val topName: String = args
    .collectFirst { case s if s.startsWith("--top=") => s.stripPrefix("--top=") }
    .getOrElse("tensor")

  println(s"Generating Verilog for Schnitzel Core (top=$topName)...")

  val outputDir = "generated"

  var topConfig: SystemConfig = null

  ChiselStage.emitSystemVerilogFile(
    topName match {
      case "tensor"  => val m = new TensorTop; topConfig = m.getConfig; m
      case "default" => val m = new Top; topConfig = m.getConfig; m
      case other     => sys.error(s"Unknown --top value '$other'.")
    },
    args = Array("--target-dir", outputDir),
    firtoolOpts = Array(
      "-disable-all-randomization",
      "-strip-debug-info",
      "--enable-layers=Verification,Verification.Assert,Verification.Assume,Verification.Cover"
    )
  )

  val pw = new PrintWriter(new File(s"$outputDir/config.json"))
  try {
    pw.write(write(topConfig, indent = 2))
    println(s"Successfully generated metadata at $outputDir/config.json")
  } finally {
    pw.close()
  }

  println(s"Verilog generated in $outputDir/")
}

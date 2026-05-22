package sim

import chisel3._
import circt.stage.ChiselStage
import top.{Top, TensorTop}
import config.SystemConfig
import upickle.default.{Writer, write}
import java.io.{File, PrintWriter}

/** Side-effecting helpers shared between this CLI driver and phs.PhsDriver.
  *
  * `writeConfigJson` and `writeBenderYml` together codify the "what we emit
  * alongside the chisel SystemVerilog output" contract — keeping them in
  * one place avoids drift between the two driver entry points and means a
  * future driver only has to call them.
  */
object EmitArtifacts {

  /** Serialize `config` to `$outputDir/config.json` via upickle. */
  def writeConfigJson[T: Writer](outputDir: String, config: T): Unit = {
    val pw = new PrintWriter(new File(s"$outputDir/config.json"))
    try {
      pw.write(write(config, indent = 2))
      println(s"Successfully generated metadata at $outputDir/config.json")
    } finally {
      pw.close()
    }
  }

  /** Emit a Bender package manifest at `$outputDir/Bender.yml` that lists
    * every `.sv` file currently present in `outputDir` (sorted).
    *
    * The root schnitzel Bender.yml depends on this as a path-dep so that
    * downstream tooling (`bender script verilator|genus|...`) sees the
    * chisel sources along with the rest of the design.
    */
  def writeBenderYml(outputDir: String): Unit = {
    val sourceFiles: Seq[String] = Option(new File(outputDir).listFiles())
      .map(_.toSeq)
      .getOrElse(Seq.empty)
      .map(_.getName)
      .filter(_.endsWith(".sv"))
      .sorted

    val pw = new PrintWriter(new File(s"$outputDir/Bender.yml"))
    try {
      pw.write("# Auto-generated alongside the chisel emit — do not edit by hand.\n")
      pw.write("package:\n")
      pw.write("  name: schnitzel_rtl\n")
      pw.write("  authors: [\"auto-generated\"]\n\n")
      pw.write("sources:\n")
      sourceFiles.foreach(f => pw.write(s"  - $f\n"))
      println(s"Successfully generated $outputDir/Bender.yml (${sourceFiles.size} files)")
    } finally {
      pw.close()
    }
  }
}

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

  val outputDir: String = args
    .collectFirst { case s if s.startsWith("--output-dir=") => s.stripPrefix("--output-dir=") }
    .getOrElse("generated")

  println(s"Generating Verilog for Schnitzel Core (top=$topName, output=$outputDir)...")

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

  EmitArtifacts.writeConfigJson(outputDir, topConfig)
  EmitArtifacts.writeBenderYml(outputDir)

  println(s"Verilog generated in $outputDir/")
}

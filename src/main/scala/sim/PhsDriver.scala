package sim

import chisel3._
import circt.stage.ChiselStage
import top.PhsTop
import upickle.default.{write, read}
import java.io.{File, PrintWriter}
import config.PhsAcceleratorConfig
import scopt.OParser

case class PhsDriverConfig(
    phsConfig: String = "",
    outputDir: String = "generated"
)

/** CLI driver for PHS hardware generation, called from phsc.
  *
  * Usage:
  *   mill 'schnitzel.runMain sim.PhsDriver' \
  *     --phs-config '<json string>' \
  *     --output-dir path/to/generated
  */
object PhsDriver {
  def main(args: Array[String]): Unit = {
    val builder = OParser.builder[PhsDriverConfig]
    val parser = {
      import builder._
      OParser.sequence(
        programName("PhsDriver"),
        opt[String]("phs-config")
          .required()
          .action((x, c) => c.copy(phsConfig = x))
          .text("PhsAcceleratorConfig as JSON string"),
        opt[String]("output-dir")
          .action((x, c) => c.copy(outputDir = x))
          .text("output directory for generated SystemVerilog (default: generated)")
      )
    }

    OParser.parse(parser, args, PhsDriverConfig()) match {
      case Some(config) => generate(config)
      case None         => sys.exit(1)
    }
  }

  def generate(config: PhsDriverConfig): Unit = {
    println("Generating Verilog for Schnitzel PHS Core...")

    val phsConfigs = read[Seq[Seq[PhsAcceleratorConfig]]](config.phsConfig)

    var topModule: PhsTop = null

    ChiselStage.emitSystemVerilogFile(
      {
        topModule = new PhsTop(phsConfigs)
        topModule
      },
      args = Array("--target-dir", config.outputDir),
      firtoolOpts = Array(
        "-disable-all-randomization",
        "-strip-debug-info"
      )
    )

    val configJson = write(topModule.getConfig, indent = 2)
    val pw = new PrintWriter(new File(s"${config.outputDir}/config.json"))
    try {
      pw.write(configJson)
      println(s"Successfully generated metadata at ${config.outputDir}/config.json")
    } finally {
      pw.close()
    }

    println(s"Verilog generated in ${config.outputDir}/Top.sv")
  }
}

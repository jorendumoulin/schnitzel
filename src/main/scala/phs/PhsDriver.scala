package phs

import chisel3._
import circt.stage.ChiselStage
import upickle.default.read
import scopt.OParser
import sim.EmitArtifacts

case class PhsDriverConfig(
    phsConfig: String = "",
    outputDir: String = "generated"
)

/** CLI driver for PHS hardware generation, called from phsc.
  *
  * Usage:
  *   mill 'schnitzel.runMain phs.PhsDriver' \
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

    EmitArtifacts.writeConfigJson(config.outputDir, topModule.getConfig)
    EmitArtifacts.writeBenderYml(config.outputDir)

    println(s"Verilog generated in ${config.outputDir}/Top.sv")
  }
}

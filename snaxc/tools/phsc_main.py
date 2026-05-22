import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from io import StringIO

from xdsl.dialects.builtin import ModuleOp
from xdsl.parser import Parser
from xdsl.passes import ModulePass, PassPipeline
from xdsl.printer import Printer
from xdsl.transforms.approximate_math_with_bitcast import ApproximateMathWithBitcastPass
from xdsl.transforms.common_subexpression_elimination import CommonSubexpressionElimination
from xdsl.transforms.mlir_opt import MLIROptPass

from snaxc.dialects import phs
from snaxc.hw.acc_context import AccContext
from snaxc.hw.config_parser import parse_config
from snaxc.hw.phs_accelerator import PhsAccelerator
from snaxc.phs.export_to_schnitzel import call_phs_driver
from snaxc.tools.snaxc_main import SNAXCMain
from snaxc.transforms.hardfloat.convert_float_to_hardfloat import ConvertFloatToHardfloatPass
from snaxc.transforms.hardfloat.convert_hardfloat_to_hw import ConvertHardfloatToHw
from snaxc.transforms.hardfloat.merge_across_array_get import MergeAcrossArrayGetPass
from snaxc.transforms.hardfloat.reconcile_recodes import ReconcileRecodesPass
from snaxc.transforms.hardfloat.split_round import SplitHardfloatRoundersPass
from snaxc.transforms.phs.convert_float_to_int import PhsConvertFloatToInt
from snaxc.transforms.phs.convert_pe_to_hw import ConvertPEToHWPass
from snaxc.transforms.phs.divf_constant_to_mul import PhsDivfConstantToMulPass
from snaxc.transforms.phs.divf_to_reciprocal_bitcast import PhsDivfToReciprocalBitcastPass
from snaxc.transforms.phs.encode import PhsEncodePass
from snaxc.transforms.phs.expand_integer_minmax import ExpandIntegerMinMaxPass
from snaxc.transforms.phs.export_phs import PhsKeepPhsPass, PhsRemovePhsPass
from snaxc.transforms.phs.finalize_phs_to_hw import FinalizePhsToHWPass
from snaxc.transforms.phs.hw_scalarize_public_modules import HwScalarizePublicModulesPass
from snaxc.transforms.phs.instantiate_pe_array import InstantiatePEArrayPass
from snaxc.transforms.phs.prune_unused_carries import PrunePEUnusedCarriesPass
from snaxc.transforms.phs.remove_one_option_switches import PhsRemoveOneOptionSwitchesPass
from snaxc.transforms.phs.schedule_preset.separate_linalg import PhsScheduleSeparateLinalgPass
from snaxc.transforms.promote_linalg_scalars import PromoteLinalgScalarsPass


def _harvest_accelerators(hardware_module: ModuleOp, pe_clones: dict[str, phs.PEOp]) -> list[PhsAccelerator]:
    """
    Build one ``PhsAccelerator`` per ``phs.pe_array`` op currently in the
    module. The TemplateSpec is read directly off the PEArrayOp; the
    abstract PE used for decode_abstract_graph is taken from ``pe_clones``
    (snapshotted before the HW-pipeline lowering passes ran, so its body
    still matches what convert_generic_body_to_phs produces at dispatch
    time).
    """
    accelerators: list[PhsAccelerator] = []
    for op in hardware_module.ops:
        if not isinstance(op, phs.PEArrayOp):
            continue
        pe_name = op.pe_ref.string_value()
        assert pe_name in pe_clones, f"No PE clone stashed for @{pe_name}"
        accelerators.append(PhsAccelerator(pe_clones[pe_name], op.get_template_spec(0)))
    return accelerators


class PHSCMain(SNAXCMain):
    def __init__(
        self,
        description: str = "Programmable Hardware Synthesis Compiler",
        args: Sequence[str] | None = None,
    ):
        # arg handling
        arg_parser = argparse.ArgumentParser(description=description)
        self.register_all_arguments(arg_parser)
        self.args = arg_parser.parse_args(args=args)

        self.ctx = AccContext(allow_unregistered=True)
        self.register_all_dialects()
        self.setup_input_pipeline()

    def run(self):
        # read file
        f = open(self.args.input_file)
        module = Parser(self.ctx, f.read(), self.get_input_name()).parse_module()
        f.close()

        # apply passes
        module.verify()
        self.input_pipeline.apply(self.ctx, module)
        module.verify()
        hardware_module = module.clone()

        # Snapshot each PEOp in its post-input-pipeline form. These clones are
        # the "abstract" PEs the software pipeline uses for switch decoding
        # (decode_abstract_graph). They have to be captured before the HW
        # pipeline rewrites the PE bodies (float→int, hardfloat lowering,
        # min/max expansion, switch pruning).
        pe_clones: dict[str, phs.PEOp] = {}
        for op in hardware_module.ops:
            if isinstance(op, phs.PEOp):
                pe_clones[op.name_prop.data] = op.clone()

        self.setup_hardware_pipeline()

        # Stage 1: HW-pipeline passes up to and including instantiate-pe-array
        # so phs.pe_array ops exist and carry the canonical TemplateSpec.
        self.pre_array_pipeline.apply(self.ctx, hardware_module)
        accelerators = _harvest_accelerators(hardware_module, pe_clones)
        # Stage 2: lower PE bodies to hw.module + rest of the hw pipeline.
        self.hardware_pipeline.apply(self.ctx, hardware_module)
        hardware_module.verify()

        # write to output
        output_hardware_stream = StringIO()
        Printer(output_hardware_stream).print_op(hardware_module)
        hardware_ir_string = output_hardware_stream.getvalue()

        # Hardware postprocessing pipeline treats circt-opt and firtool as black box
        # Because the output after circt-opt can not be parsed by xdsl,
        # and for sure the systemverilog after firtool can not be parsed by xdsl.

        os.makedirs(os.path.dirname(os.path.abspath(self.args.output_hardware)), exist_ok=True)

        if not self.args.no_sv_conversion:
            p1 = subprocess.Popen(
                ["circt-opt", "--map-arith-to-comb", "--hw-flatten-modules"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            p2 = subprocess.Popen(
                ["firtool", "--format=mlir", "--strip-debug-info"],
                stdin=p1.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            assert p1.stdout is not None
            p1.stdout.close()
            _, p1_stderr = p1.communicate(input=hardware_ir_string)
            if p1.returncode != 0:
                print(
                    f"Error during hardware conversion (circt-opt):\n{p1_stderr}",
                    file=sys.stderr,
                )
                raise SystemExit(p1.returncode or 1)
            stdout_final, stderr_final = p2.communicate()
            if p2.returncode != 0:
                print(
                    f"Error during hardware conversion (firtool):\n{stderr_final}",
                    file=sys.stderr,
                )
                raise SystemExit(p2.returncode or 1)
            else:
                with open(self.args.output_hardware, "w") as outfile:
                    outfile.write(stdout_final)
                # Verilator resolves unknown modules by filename autodiscovery
                # (looks for `<module_name>.sv` on its -y/-I path). firtool packs
                # every `hw.module` into the single output above, so for multi-PE
                # designs only one module is auto-findable. Split the consolidated
                # output into per-module files named after each module so all PHS
                # blackboxes are picked up by the simulator build.
                self._split_sv_per_module(stdout_final, os.path.dirname(os.path.abspath(self.args.output_hardware)))

        else:
            with open(self.args.output_hardware, "w") as outfile:
                outfile.write(hardware_ir_string)

        # Generate schnitzel SoC verilog if requested
        if self.args.output_schnitzel_dir:
            system_config = call_phs_driver(accelerators, self.args.output_hardware, self.args.output_schnitzel_dir)
            assert isinstance(self.ctx, AccContext)
            self.ctx.system = parse_config(system_config)

            # Replace the Phs accelerator from config with the full PhsAccelerator
            # (which has the PEOp and TemplateSpec needed for code generation).
            # The HW generator assigns the CSR base, so copy it across before
            # swapping so that param_values() uses the correct absolute base.
            for acc in accelerators:
                for core in self.ctx.system.clusters[0].cores:
                    for i, sys_acc in enumerate(core.accelerators):
                        if sys_acc.name == acc.phs.name:
                            from snaxc.hw.accelerators.phs import Phs

                            if isinstance(sys_acc, Phs):
                                acc.phs.csr_base = sys_acc.csr_base
                            core.accelerators[i] = acc
                            acc.resolve_parents(core)
                            break

        # Software pipeline depends on accelerators being registered in
        # ctx.system, which only happens after call_phs_driver above.
        self.setup_software_pipeline()

        # If an optional explicit software file is requested, overwrite the previous module
        if self.args.software_file:
            f = open(self.args.software_file)
            module = Parser(self.ctx, f.read(), self.args.software_file).parse_module()
            f.close()

        self.software_pipeline.apply(self.ctx, module)
        module.verify()

        output_software_stream = open(self.args.output_file, "w")
        Printer(output_software_stream).print_op(module)
        output_software_stream.write("\n")
        output_software_stream.flush()

        # Go to

        if output_software_stream is not sys.stdout:
            output_software_stream.close()

    @staticmethod
    def _split_sv_per_module(sv_text: str, out_dir: str) -> None:
        """Write each top-level `module <name>(...)endmodule` block to its own
        `<out_dir>/<name>.sv` so Verilator can autodiscover BlackBox modules."""
        import re

        os.makedirs(out_dir, exist_ok=True)
        starts = [m for m in re.finditer(r"^module\s+(\w+)\s*\(", sv_text, flags=re.MULTILINE)]
        for idx, m in enumerate(starts):
            name = m.group(1)
            begin = m.start()
            end = starts[idx + 1].start() if idx + 1 < len(starts) else len(sv_text)
            with open(os.path.join(out_dir, f"{name}.sv"), "w") as f:
                f.write(sv_text[begin:end])

    def register_all_arguments(self, arg_parser: argparse.ArgumentParser):
        """
        Registers all the command line arguments that are used by this tool.

        Add other/additional arguments by overloading this function.
        """

        super().register_all_arguments(arg_parser)

        arg_parser.add_argument("schedule_file", type=str, nargs="?", help="path to schedule file")
        arg_parser.add_argument(
            "--scheduling-preset",
            type=str,
            choices=["separate-linalg"],
            default=None,
            help="Use a built-in scheduling pass instead of a transform-dialect schedule file. "
            "'separate-linalg' assigns every unannotated linalg.generic its own @accN accelerator.",
        )
        arg_parser.add_argument(
            "--software-file",
            type=str,
            nargs="?",
            help="path to separate other software stream,"
            " by default the same input stream is used for hard- and software",
        )
        arg_parser.add_argument("--output-hardware", type=str, required=True, help="path to output hardware")
        arg_parser.add_argument(
            "--no-sv-conversion", action="store_true", help="Don't convert output hardware to systemverilog"
        )
        arg_parser.add_argument(
            "--easyfloat-path", type=str, nargs="?", help="Set custom path to kuleuven-easyfloat installation"
        )
        arg_parser.add_argument(
            "--hardfloat-external-modules", action="store_true", help="Instantiate hardfloat modules as external"
        )
        arg_parser.add_argument(
            "--output-schnitzel-dir",
            type=str,
            nargs="?",
            help="generate schnitzel SoC verilog in this directory (calls PhsDriver via mill)",
        )

    """
    The pipelines of this compiler are as follows

    ```
    no software file provided:                  | software file provided:
    input file is input for both sw and hw flow | input file is for hardware, software_file for sw flow
                                                |
    input_file,                                 | input_file
    schedule_file,                              | schedule_file                 software_file
      V                                         | V                             V
      | <- input pipeline                       | | <- input pipeline           |
      |    Register accelerators                | | <- Register accelerators -> | <- software pipeline
      *                                         | |                             |
      |\\                                       | |                             x input_file_preprocessed.mlir
      | \\                                      | |
      | | <- hardware pipeline                  | | <- hardware pipeline
      | |                                       | |
      | x acc_array.mlir                        | x acc_array.mlir
      | |                                       | |
      | | <- hardware postprocessing pipeline   | | <- hardware postprocessing pipeline
      | |                                       | |
      | x acc_array.sv                          | x acc_array.sv
      |                                         |
      | <- software pipeline                    |
      |                                         |
      x input_file_preprocessed.mlir            |
    ```

    Fails, if not all passes are registered.
    """

    def setup_input_pipeline(self):
        """
        Create input pipeline.
        The input pipeline annotates and encodes relevant linalg ops into PHS
        """
        if (self.args.schedule_file is None) == (self.args.scheduling_preset is None):
            raise SystemExit("Exactly one of <schedule_file> or --scheduling-preset must be provided.")

        input_pass_pipeline: list[ModulePass] = []

        if self.args.scheduling_preset is None:
            # Transform-dialect path: load the user's schedule.mlir and run
            # the transform interpreter to apply it.
            input_pass_pipeline.append(
                MLIROptPass(
                    arguments=(
                        "--linalg-generalize-named-ops",
                        f"--transform-preload-library=transform-library-paths={self.args.schedule_file}",
                        "--transform-interpreter",
                    )
                )
            )
        else:
            # Preset path: still generalize named ops, then run the chosen
            # built-in scheduling pass (no transform dialect involved).
            input_pass_pipeline.append(MLIROptPass(arguments=("--linalg-generalize-named-ops",)))
            if self.args.scheduling_preset == "separate-linalg":
                input_pass_pipeline.append(PhsScheduleSeparateLinalgPass())
            else:
                raise SystemExit(f"Unknown scheduling preset: {self.args.scheduling_preset}")
        input_pass_pipeline.append(PromoteLinalgScalarsPass())
        # Rewrite `arith.divf %x, %const` as `arith.mulf %x, 1/const`. Runs
        # before PHS encoding so the rewrite operates on plain linalg/arith
        # IR. Assumes reciprocal accuracy is acceptable for NN inference.
        input_pass_pipeline.append(PhsDivfConstantToMulPass())
        # Replace `math.exp`/`math.log` with bitcast-trick approximations. The
        # PHS hardware path has no transcendental ops; this lowers them to
        # mul/add/fptosi/bitcast which already lower through hardfloat.
        input_pass_pipeline.append(ApproximateMathWithBitcastPass())
        # Approximate any remaining `arith.divf` (e.g. softmax 1/sum_exp) as
        # `%a * recip(%b)` via the Schraudolph bitcast trick plus one Newton
        # iteration.
        input_pass_pipeline.append(PhsDivfToReciprocalBitcastPass())
        input_pass_pipeline.append(PhsEncodePass())
        # Drops carry-input slots whose data is unused in the merged PE body
        # (lowering them from `readWrite` to plain `write`). Defense-in-depth:
        # the Scala accelerator separately handles unused carries via its
        # per-streamer `carryUsed` gating, but pruning is still preferred —
        # it saves an extra TCDM read per dead carry per cycle. The new
        # paired_outputs representation lets us drop carries at any output
        # position, not just trailing ones.
        input_pass_pipeline.append(PrunePEUnusedCarriesPass())
        self.input_pipeline = PassPipeline(tuple(input_pass_pipeline), self.pipeline_callback)

    def setup_hardware_pipeline(self):
        # Split into two stages. Stage 1 ends at instantiate-pe-array so the
        # accelerator harvest can read the canonical TemplateSpec directly
        # off the freshly-built phs.pe_array. The PE-body lowering passes
        # (PhsConvertFloatToInt, hardfloat, min/max, remove-one-option-
        # switches) stay in stage 1 because they mutate the same PEOp the
        # PEArrayOp instances refer to — running them before
        # instantiate-pe-array keeps the array body's phs.instance ops in
        # sync.
        pre_pipeline: list[ModulePass] = []
        pre_pipeline.append(PhsConvertFloatToInt())
        pre_pipeline.append(ConvertFloatToHardfloatPass())
        # Lower integer min/max to cmpi+select; circt-opt's --map-arith-to-comb
        # rejects `arith.maxsi`/`minsi`/`maxui`/`minui`.
        pre_pipeline.append(ExpandIntegerMinMaxPass())
        pre_pipeline.append(PhsRemoveOneOptionSwitchesPass())
        # Run before phs-keep-phs so the originating linalg.generics (which
        # carry the affine maps and bounds for each dataflow mode) are still
        # present when the array is built.
        pre_pipeline.append(InstantiatePEArrayPass())
        self.pre_array_pipeline = PassPipeline(tuple(pre_pipeline), self.pipeline_callback)

        hardware_pass_pipeline: list[ModulePass] = []
        hardware_pass_pipeline.append(PhsKeepPhsPass())
        hardware_pass_pipeline.append(ConvertPEToHWPass())
        hardware_pass_pipeline.append(FinalizePhsToHWPass())
        # Split fused `add_rec_fn` / `mul_rec_fn` so the rounder becomes a
        # standalone op. This exposes the rounder for sharing in the next
        # pass and lets CSE collapse identical `recode_to_raw` ops.
        hardware_pass_pipeline.append(SplitHardfloatRoundersPass())
        # Share hardfloat ops across mutex `phs.choose` lanes that the
        # finalize pass has just turned into `array_get(array_create(...))`:
        # rounders, addf/subf, sitofp/uitofp, fptosi/fptoui all collapse via
        # a single shared instance + per-operand mux.
        hardware_pass_pipeline.append(MergeAcrossArrayGetPass())
        # Dedupe identical pure ops (notably hardfloat ops) that previously
        # lived in mutex `phs.choose` regions and ended up at the same scope
        # after the finalize pass inlined them. Lossless and unconditional.
        hardware_pass_pipeline.append(CommonSubexpressionElimination())
        hardware_pass_pipeline.append(ReconcileRecodesPass())
        if self.args.easyfloat_path is None:
            tool_dir = os.path.dirname(__file__)
            easyfloat_path = os.path.abspath(os.path.join(tool_dir, "..", "..", "..", "kuleuven-easyfloat"))
        else:
            easyfloat_path = self.args.easyfloat_path
        hardware_pass_pipeline.append(
            ConvertHardfloatToHw(easyfloat_path=easyfloat_path, external_modules=self.args.hardfloat_external_modules)
        )
        hardware_pass_pipeline.append(FinalizePhsToHWPass())
        hardware_pass_pipeline.append(HwScalarizePublicModulesPass())
        self.hardware_pipeline = PassPipeline(tuple(hardware_pass_pipeline), self.pipeline_callback)

    def setup_software_pipeline(self):
        software_pass_pipeline: list[ModulePass] = []
        software_pass_pipeline.append(PhsRemovePhsPass())

        # Get the normal pipeline from SNAXC
        super().setup_pipeline(phs=True)
        software_pass_pipeline.extend(self.pipeline.passes)
        self.software_pipeline = PassPipeline(tuple(software_pass_pipeline), self.pipeline_callback)

    def pipeline_callback(self, previous_pass: ModulePass, module: ModuleOp, next_pass: ModulePass) -> None:
        module.verify()
        if self.args.print_between_passes:
            print(f"// IR after {previous_pass.name}:")
            printer = Printer(stream=sys.stdout)
            printer.print_op(module)
            print("\n\n\n")


def main():
    PHSCMain().run()


if "__main__" == __name__:
    main()

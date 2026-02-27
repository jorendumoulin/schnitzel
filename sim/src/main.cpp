#include "sim.h"
#include <argparse/argparse.hpp>
#include <string>
#include <vector>

int main(int argc, char *argv[]) {

  std::string version = "0.0.1";

  // Define command-line arguments
  argparse::ArgumentParser program("sim", version);

  program.add_argument("--verbose").flag().help("enable verbose output");

  unsigned long max_cycles;
  program.add_argument("--max-cycles")
      .store_into(max_cycles)
      .default_value(0)
      .help("maximum simulation cycles (0 for unlimited)");

  program.add_argument("--vcd").flag().help("enable vcd tracing");

  program.add_argument("program")
      .help("target program to simulate")
      .nargs(argparse::nargs_pattern::at_least_one);

  // This collects everything else and passes it to verilator context
  program.add_argument("--vltargs").default_value(std::string(""));
  // Parse command-line arguments
  try {
    program.parse_args(argc, argv);
  } catch (const std::exception &e) {
    std::cerr << e.what() << std::endl;
    return 1;
  }

  try {
    // Create simulator
    auto program_args = program.get<std::vector<std::string>>("program");
    auto verilator_args = program.get<std::string>("vltargs");
    Sim sim(program_args, verilator_args);

    // Configure
    sim.set_verbose(program.get<bool>("verbose"));
    sim.set_max_cycles(max_cycles);
    if (program.get<bool>("vcd")) {
      sim.enable_trace("./sim.vcd");
    }

    // Run simulation
    return sim.run();

  } catch (const std::exception &e) {
    fprintf(stderr, "Error: %s\n", e.what());
    return 1;
  }

  return 0;
}

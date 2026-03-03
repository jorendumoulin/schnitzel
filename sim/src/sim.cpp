#include "sim.h"
#include "dpi_memory.h"
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>

Sim::Sim(const std::vector<std::string> &args, const std::string &vltargs)
    : dut(nullptr), context(nullptr), trace(nullptr), cycle_count(0),
      max_cycles(0), verbose(false) {

  std::stringstream ss(vltargs);
  std::vector<std::string> v_args_vec;
  std::string tmp;
  while (ss >> tmp) {
    v_args_vec.push_back(tmp);
  }
  std::vector<char *> c_args;
  static char dummy_name[] = "sim";
  c_args.push_back(dummy_name);

  for (auto &arg : v_args_vec) {
    c_args.push_back(arg.data());
  }
  init_core(c_args.size(), c_args.data());

  dpi_memory_init();
  for (auto prog : args) {
    dpi_memory_load_program(prog.c_str());
  }
}

Sim::~Sim() { cleanup_core(); }

void Sim::init_core(int argc, char **argv) {
  context = new VerilatedContext;
  context->commandArgs(argc, argv);

  dut = new VTopWrapper(context);

  dut->clock = 0;
  dut->reset = 0;

  dut->eval();
}

void Sim::cleanup_core() {
  if (dut) {
    dut->final();
    delete dut;
  }
  if (context) {
    delete context;
  }
}

void Sim::reset() {
  dut->reset = 1;
  for (int i = 0; i < 8; i++) {
    tick();
  }
  dut->reset = 0;
  tick();

  cycle_count = 0;
}

void Sim::tick() {
  dut->clock = 1;
  dut->eval();
  if (trace) {
    trace->dump(context->time());
  }
  context->timeInc(1);

  dut->clock = 0;
  dut->eval();
  if (trace) {
    trace->dump(context->time());
  }
  context->timeInc(1);

  cycle_count++;
}

int Sim::run() {
  if (verbose) {
    fprintf(stderr, "Resetting core...\n");
  }

  reset();

  if (verbose) {
    fprintf(stderr, "Starting simulation...\n");
  }

  while (true) {
    if (dpi_check_host_exit()) {
      if (verbose) {
        fprintf(stderr, "Exit requested via tohost\n");
      }
      break;
    }

    if (max_cycles > 0 && cycle_count >= max_cycles) {
      if (verbose) {
        fprintf(stderr, "Reached maximum cycles: %lu\n", cycle_count);
      }
      break;
    }

    tick();

    if (verbose && (cycle_count % 10000) == 0) {
      fprintf(stderr, "Cycle: %lu\n", cycle_count);
    }
  }

  if (trace) {
    if (verbose) {
      fprintf(stderr, "Closing VCD trace\n");
    }
    trace->close();
    delete trace;
    trace = nullptr;
  }

  if (verbose) {
    fprintf(stderr, "Simulation finished after %lu cycles\n", cycle_count);
  }

  return 0;
}

void Sim::enable_trace(const char *filename) {
  if (verbose) {
    fprintf(stderr, "Enabling VCD tracing to %s\n", filename);
  }
  context->traceEverOn(true);
  trace = new VerilatedVcdC;
  dut->trace(trace, 99);
  trace->open(filename);
}

void Sim::log(const char *format, ...) {
  if (!verbose)
    return;

  va_list args;
  va_start(args, format);
  vfprintf(stderr, format, args);
  va_end(args);
}

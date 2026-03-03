#ifndef __SIM_H
#define __SIM_H

#include <VTopWrapper.h>
#include <cstdint>
#include <string>
#include <vector>
#include <verilated.h>
#include <verilated_vcd_c.h>

class Sim {
public:
  Sim(const std::vector<std::string> &args, const std::string &vltargs);
  virtual ~Sim();

  int run();

  void enable_trace(const char *filename);
  void set_verbose(bool v) { verbose = v; }
  void set_max_cycles(uint64_t cycles) { max_cycles = cycles; }

protected:
  void reset();

private:
  VTopWrapper *dut;
  VerilatedContext *context;
  VerilatedVcdC *trace;

  uint64_t cycle_count;
  uint64_t max_cycles;
  bool verbose;

  void tick();
  void init_core(int argc, char **argv);
  void cleanup_core();
  void log(const char *format, ...);
};

#endif

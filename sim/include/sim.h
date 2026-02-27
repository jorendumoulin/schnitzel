// See LICENSE for license details.

#ifndef __SIM_H
#define __SIM_H

// #include "axi_interface.h"
#include "dynamic_memory.h"
#include <VTop.h>
#include <cstdint>
#include <elfio/elfio.hpp>
#include <loader.h>
#include <memory>
#include <string>
#include <vector>
#include <verilated.h>
#include <verilated_vcd_c.h>

// Forward declarations for Verilator
// class VCore;
// class VerilatedContext;
// class VerilatedVcdC;

/** spitchel_t: RISC-V simulator using verilated Schnitzel core
 *
 * This class integrates the verilated Schnitzel RISC-V core with spike's
 * fesvr infrastructure, allowing us to run real RISC-V binaries on the
 * hardware implementation.
 *
 * The class bridges between:
 * - fesvr's memory interface (for loading ELF, syscalls)
 * - Schnitzel's BusIO interface (for instruction/data memory)
 */
class Sim {
public:
  /** Constructor with vector of arguments
   * @param args Command line arguments
   */
  Sim(const std::vector<std::string> &args, const std::string &vltargs);

  /** Destructor */
  virtual ~Sim();

  /** Main simulation loop
   * @return Exit code from the simulated program
   */
  int run();

  /** Enable/disable VCD tracing
   * @param filename VCD file to write to (nullptr to disable)
   */
  void enable_trace(const char *filename);

  /** Set verbose logging mode */
  void set_verbose(bool v) { verbose = v; }

  /** Set maximum number of cycles to simulate (0 = unlimited) */
  void set_max_cycles(uint64_t cycles) { max_cycles = cycles; }

  /** Add an AXI interface to this simulation
   * @param axi_interface Pointer to AXI interface (takes ownership)
   */
  // void add_axi_interface(std::unique_ptr<AxiInterface> axi_interface);

protected:
  /** Reset the core to initial state */
  void reset();

private:
  // ========================================
  // Verilator components
  // ========================================

  /** Verilated core instance */
  VTop *dut;

  /** Verilator context */
  VerilatedContext *context;

  /** VCD trace file */
  VerilatedVcdC *trace;

  DynamicMemory memory;
  Loader loader;

  // ========================================
  // Simulation state
  // ========================================

  /** Current simulation cycle count */
  uint64_t cycle_count;

  /** Maximum cycles to simulate (0 = unlimited) */
  uint64_t max_cycles;

  /** Instruction count */
  uint64_t instr_count;

  /** Verbose logging enabled */
  bool verbose;

  /** Simulation has finished */
  bool sim_finished;

  // ========================================
  // AXI interfaces
  // ========================================

  /** AXI interfaces attached to this simulation */
  // std::vector<std::unique_ptr<AxiInterface>> axi_interfaces;

  // ========================================
  // Core interaction methods
  // ========================================

  /** Load bootrom into memory */
  void load_bootrom();

  /** Advance simulation by one clock cycle */
  void tick();

  int handle_host();

  /** Initialize the verilated core */
  void init_core(int argc, char **argv);

  /** Cleanup verilated core */
  void cleanup_core();

  void wide_mem_response();
  void wide_mem_transaction();

  // Wide Memory interface (512 bits)
  uint64_t wide_addr = 0;
  uint64_t wide_strb = 0;
  alignas(8) uint8_t wide_data[64];
  bool wide_response_pending = false;

  void narrow_mem_response();
  void narrow_mem_transaction();

  // Narrow Memory interface (64 bits)
  uint64_t narrow_addr = 0;
  uint64_t narrow_strb = 0;
  uint64_t narrow_data = 0;
  bool narrow_response_pending = false;

  // ========================================
  // Debugging/logging helpers
  // ========================================

  /** Log a message if verbose is enabled */
  void log(const char *format, ...);

  /** Print core state for debugging */
  void print_core_state();
};

#endif // __SIM_H

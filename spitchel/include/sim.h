// See LICENSE for license details.

#ifndef __SPITCHEL_H
#define __SPITCHEL_H

#include <VTop.h>
#include <cstdint>
#include <elfio/elfio.hpp>
#include <loader.h>
#include <memory.h>
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
  Sim(const std::vector<std::string> &args);

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

  Memory memory;
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
  // Bus interface state
  // ========================================

  /** Pending wide axi request */
  bool axi_wide_req_pending;
  size_t axi_wide_req_addr;

  /** Pending axi_2 request */
  bool axi_wide_2_req_pending;
  bool axi_wide_2_write_rsp_pending = false;
  size_t axi_wide_2_req_addr;
  // bool dmem_req_wen;
  // uint64_t dmem_req_wdata;

  /** Pending data memory request */
  bool dmem_req_pending;
  size_t dmem_req_addr;
  bool dmem_req_wen;
  uint64_t dmem_req_wdata;

  // ========================================
  // Core interaction methods
  // ========================================

  /** Load bootrom into memory */
  void load_bootrom();

  /** Advance simulation by one clock cycle */
  void tick();

  /** Handle axi wide requests */
  void handle_axi_wide();
  bool axi_wide_response_next;
  VlWide<16> axi_wide_response_data;

  void handle_axi_wide_2();
  bool axi_wide_2_response_next;
  uint64_t axi_wide_2_write_addr;
  bool axi_wide_2_write_pending = false;
  VlWide<16> axi_wide_2_response_data;

  /** Handle data memory bus requests */
  void handle_dmem();
  bool dmem_response_next;
  uint32_t dmem_response_data;

  int handle_host();

  /** Initialize the verilated core */
  void init_core();

  /** Cleanup verilated core */
  void cleanup_core();

  // ========================================
  // Debugging/logging helpers
  // ========================================

  /** Log a message if verbose is enabled */
  void log(const char *format, ...);

  /** Print core state for debugging */
  void print_core_state();
};

#endif // __SPITCHEL_H

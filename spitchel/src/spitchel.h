// See LICENSE for license details.

#ifndef __SPITCHEL_H
#define __SPITCHEL_H

#include <cstdint>
#include <fesvr/htif.h>
#include <fesvr/memif.h>
#include <memory>
#include <string>
#include <vector>

// Forward declarations for Verilator
class VCore;
class VerilatedContext;
#ifdef ENABLE_TRACE
class VerilatedVcdC;
#endif

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
class spitchel_t : public htif_t {
public:
  /** Constructor
   * @param argc Command line argument count
   * @param argv Command line arguments
   */
  spitchel_t(int argc, char **argv);

  /** Constructor with vector of arguments
   * @param args Command line arguments
   */
  spitchel_t(const std::vector<std::string> &args);

  /** Destructor */
  virtual ~spitchel_t();

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
  // ========================================
  // Required htif_t virtual method overrides
  // ========================================

  /** Reset the core to initial state */
  virtual void reset() override;

  /** Read a chunk of memory
   * @param taddr Target address
   * @param len Length to read
   * @param dst Destination buffer
   */
  virtual void read_chunk(addr_t taddr, size_t len, void *dst) override;

  /** Write a chunk of memory
   * @param taddr Target address
   * @param len Length to write
   * @param src Source buffer
   */
  virtual void write_chunk(addr_t taddr, size_t len, const void *src) override;

  /** Clear a chunk of memory (fill with zeros)
   * @param taddr Target address
   * @param len Length to clear
   */
  virtual void clear_chunk(addr_t taddr, size_t len) override;

  /** Get chunk alignment requirement */
  virtual size_t chunk_align() override { return 8; }

  /** Get maximum chunk size */
  virtual size_t chunk_max_size() override { return 64; }

  /** Idle function called during simulation */
  virtual void idle() override;

private:
  // ========================================
  // Verilator components
  // ========================================

  /** Verilated core instance */
  VCore *core;

  /** Verilator context */
  VerilatedContext *context;

#ifdef ENABLE_TRACE
  /** VCD trace file */
  VerilatedVcdC *trace;
#endif

  // ========================================
  // Memory subsystem
  // ========================================

  /** Main memory storage */
  std::vector<uint8_t> mem;

  /** Base address of memory */
  addr_t mem_base;

  /** Size of memory in bytes */
  size_t mem_size;

  /** Check if address is in valid memory range */
  bool is_valid_addr(addr_t addr, size_t len) const;

  /** Convert target address to memory array offset */
  size_t addr_to_offset(addr_t addr) const;

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

  /** Pending instruction memory request */
  bool imem_req_pending;
  addr_t imem_req_addr;

  /** Pending data memory request */
  bool dmem_req_pending;
  addr_t dmem_req_addr;
  bool dmem_req_wen;
  uint64_t dmem_req_wdata;

  // ========================================
  // Core interaction methods
  // ========================================

  /** Advance simulation by one clock cycle */
  void tick();

  /** Handle instruction memory bus requests */
  void handle_imem();

  /** Handle data memory bus requests */
  void handle_dmem();

  /** Check for HTIF communication (tohost/fromhost) */
  void check_htif();

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

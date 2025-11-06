#include "spitchel.h"
#include <VCore.h>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <verilated.h>
#include <verilated_vcd_c.h>

spitchel_t::spitchel_t(const std::vector<std::string> &args)
    : htif_t(args), core(nullptr), context(nullptr), trace(nullptr),
      mem_base(0x1000), mem_size(128 * 1024 * 1024), cycle_count(0),
      max_cycles(0), instr_count(0), verbose(false), sim_finished(false),
      imem_req_pending(false), dmem_req_pending(false) {

  mem.resize(mem_size, 0);
  init_core();
}

spitchel_t::~spitchel_t() { cleanup_core(); }

void spitchel_t::init_core() {
  context = new VerilatedContext;
  core = new VCore(context);

  // Initialize signals
  core->clock = 0;
  core->reset = 0;
  core->io_imem_req_ready = 0;
  core->io_imem_rsp_data = 0;
  core->io_dmem_req_ready = 0;
  core->io_dmem_rsp_data = 0;

  core->eval();
}

void spitchel_t::cleanup_core() {
  if (core) {
    core->final();
    delete core;
  }
  if (context) {
    delete context;
  }
}

void spitchel_t::reset() {
  // Reset the core
  core->reset = 1;
  tick();
  tick();
  core->reset = 0;
  tick();

  cycle_count = 0;
  instr_count = 0;
  sim_finished = false;
}

bool spitchel_t::is_valid_addr(addr_t addr, size_t len) const {
  if (addr < mem_base)
    return false;
  if (addr + len < addr)
    return false; // overflow
  if (addr + len > mem_base + mem_size)
    return false;
  return true;
}

size_t spitchel_t::addr_to_offset(addr_t addr) const { return addr - mem_base; }

void spitchel_t::read_chunk(addr_t taddr, size_t len, void *dst) {
  if (!is_valid_addr(taddr, len)) {
    memset(dst, 0, len);
    return;
  }

  size_t offset = addr_to_offset(taddr);
  memcpy(dst, &mem[offset], len);
}

void spitchel_t::write_chunk(addr_t taddr, size_t len, const void *src) {
  if (verbose) {
    log("WRITE CHUNK: addr=0x%lx len=%lu\n", taddr, len);
  }

  if (!is_valid_addr(taddr, len)) {
    if (verbose) {
      log("  Invalid address, write ignored\n");
    }
    return;
  }

  size_t offset = addr_to_offset(taddr);
  memcpy(&mem[offset], src, len);
}

void spitchel_t::clear_chunk(addr_t taddr, size_t len) {
  if (!is_valid_addr(taddr, len)) {
    return;
  }

  size_t offset = addr_to_offset(taddr);
  memset(&mem[offset], 0, len);
}

void spitchel_t::tick() {
  // Drive low phase
  core->clock = 0;
  core->eval();
  if (trace) {
    trace->dump(context->time());
  }
  context->timeInc(1);

  // Drive high phase
  core->clock = 1;
  core->eval();
  if (trace) {
    trace->dump(context->time());
  }
  context->timeInc(1);

  cycle_count++;
}

void spitchel_t::handle_imem() {
  // Always ready to serve instruction requests
  core->io_imem_req_ready = 1;

  if (core->io_imem_req_valid) {
    uint64_t addr = core->io_imem_req_bits_addr;

    if (is_valid_addr(addr, 4)) {
      size_t offset = addr_to_offset(addr);
      uint32_t instr = *(uint32_t *)&mem[offset];
      core->io_imem_rsp_data = instr;

      if (verbose) {
        log("IMEM: addr=0x%lx instr=0x%08x\n", addr, instr);
      }
    } else {
      core->io_imem_rsp_data = 0;
      if (verbose) {
        log("IMEM: invalid address 0x%lx\n", addr);
      }
    }
  }
}

void spitchel_t::handle_dmem() {
  // Always ready to serve data requests
  core->io_dmem_req_ready = 1;

  if (core->io_dmem_req_valid) {
    uint64_t addr = core->io_dmem_req_bits_addr;

    if (core->io_dmem_req_bits_wen) {
      // Write request
      if (is_valid_addr(addr, 8)) {
        size_t offset = addr_to_offset(addr);
        uint64_t data = core->io_dmem_req_bits_wdata;
        *(uint64_t *)&mem[offset] = data;

        if (verbose) {
          log("DMEM WRITE: addr=0x%lx data=0x%016lx\n", addr, data);
        }
      }
    } else if (core->io_dmem_req_bits_ren) {
      // Read request
      if (is_valid_addr(addr, 8)) {
        size_t offset = addr_to_offset(addr);
        uint64_t data = *(uint64_t *)&mem[offset];
        core->io_dmem_rsp_data = data;

        if (verbose) {
          log("DMEM READ: addr=0x%lx data=0x%016lx\n", addr, data);
        }
      } else {
        core->io_dmem_rsp_data = 0;
      }
    }
  }
}

void spitchel_t::check_htif() {
  // HTIF communication happens through memory-mapped tohost/fromhost
  // This is handled by the htif_t base class
}

void spitchel_t::idle() {
  // Called periodically by htif_t
  // Could add progress updates here
}

// Bootloader binary provided by cmake build process
extern unsigned char bootrom_data[];
extern unsigned int bootrom_data_len;

void spitchel_t::load_bootrom() {
  write_chunk(0x1000, bootrom_data_len, bootrom_data);
}

int spitchel_t::run() {

  if (verbose) {
    fprintf(stderr, "Loading program...\n");
  }

  // Load the bootloader and program into memory
  load_bootrom();

  // Load the program via htif
  load_program();

  if (verbose) {
    uint32_t e = get_entry_point();
    log("Entry point at 0x%x\n", e);
  }

  if (verbose) {
    fprintf(stderr, "Resetting core...\n");
  }

  // Reset the core
  reset();

  if (verbose) {
    fprintf(stderr, "Starting simulation...\n");
  }

  // Main simulation loop
  while (!done() && !sim_finished) {
    // Handle bus interfaces before clock tick
    handle_imem();
    handle_dmem();

    // Clock tick
    tick();

    // Check for HTIF activity
    check_htif();

    // Check max cycles limit
    if (max_cycles > 0 && cycle_count >= max_cycles) {
      if (verbose) {
        fprintf(stderr, "Reached maximum cycles: %lu\n", cycle_count);
      }
      break;
    }

    // Periodic progress update
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

  return exit_code();
}

void spitchel_t::enable_trace(const char *filename) {
  if (verbose) {
    fprintf(stderr, "Enabling VCD tracing to %s\n", filename);
  }
  context->traceEverOn(true);
  trace = new VerilatedVcdC;
  core->trace(trace, 99);
  trace->open(filename);
  trace->dump(context->time());
}

void spitchel_t::log(const char *format, ...) {
  if (!verbose)
    return;

  va_list args;
  va_start(args, format);
  vfprintf(stderr, format, args);
  va_end(args);
}

void spitchel_t::print_core_state() {
  if (!verbose)
    return;

  fprintf(stderr, "Cycle: %lu, PC: 0x%lx\n", cycle_count,
          (uint64_t)core->io_imem_req_bits_addr);
}

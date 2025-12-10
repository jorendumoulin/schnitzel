#include "sim.h"
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

Sim::Sim(const std::vector<std::string> &args)
    : dut(nullptr), context(nullptr), trace(nullptr), cycle_count(0),
      memory(1024 * 1024 * 1024), max_cycles(0), instr_count(0), verbose(false),
      sim_finished(false), axi_wide_req_pending(false), dmem_req_pending(false),
      axi_wide_response_next(false), dmem_response_next(false) {

  init_core();
  loader.load_program(args[0], memory);
}

Sim::~Sim() { cleanup_core(); }

void Sim::init_core() {
  context = new VerilatedContext;
  context->commandArgs(0, (char **)nullptr);

  dut = new VTop(context);

  // Initialize signals (all default to 0 in verilator)
  dut->clock = 0;
  dut->reset = 0;
  dut->io_axi_ar_ready = 0;

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
  // Reset the core
  dut->reset = 1;
  tick();
  tick();
  dut->reset = 0;
  tick();

  cycle_count = 0;
  instr_count = 0;
  sim_finished = false;
}

void Sim::tick() {
  // Drive low phase
  dut->clock = 0;
  dut->eval();
  if (trace) {
    trace->dump(context->time());
  }
  context->timeInc(1);

  // Drive high phase
  dut->clock = 1;
  dut->eval();
  if (trace) {
    trace->dump(context->time());
  }
  context->timeInc(1);

  cycle_count++;
}

void Sim::handle_axi_wide() {
  // // Always ready to serve requests
  // dut->io_axi_wide_ar_ready = 1;

  // // Serve response
  // if (axi_wide_response_next) {
  //   dut->io_axi_wide_r_bits_data = axi_wide_response_data;
  //   dut->io_axi_wide_r_valid = 1;
  //   axi_wide_response_next = false;
  // } else {
  //   // dut->io_imem_rsp_valid = 0;
  //   dut->io_axi_wide_r_valid = 0;
  // }

  // // Get request
  // if (dut->io_axi_wide_ar_valid) {
  //   uint64_t addr = dut->io_axi_wide_ar_bits_addr;

  //   size_t offset = addr;
  //   axi_wide_response_next = true;
  //   memory.read_chunk(offset, 64, axi_wide_response_data);
  //   // imem_response_data = memory.read_word(offset);

  //   if (verbose) {
  //     log("IMEM: addr=0x%lx instr=0x%08x\n", addr, axi_wide_response_data);
  //   }
  // }
}

void Sim::handle_axi_wide_2() {
  // Always ready to serve requests
  dut->io_axi_ar_ready = 1;
  dut->io_axi_aw_ready = 1;
  dut->io_axi_w_ready = 1;

  // Serve response
  if (axi_wide_2_response_next) {
    dut->io_axi_r_bits_data = axi_wide_2_response_data;
    dut->io_axi_r_valid = 1;
    dut->io_axi_r_bits_id = axi_wide_2_response_id_next;
    axi_wide_2_response_next = false;
    if (verbose) {
      log("DMEM read resp\n");
    }
  } else {
    // dut->io_imem_rsp_valid = 0;
    dut->io_axi_r_valid = 0;
  }

  // Get request
  if (dut->io_axi_ar_valid) {
    uint64_t addr = dut->io_axi_ar_bits_addr;

    // ignore transfer size for now, just send back whole 512 bits

    size_t offset = addr;
    axi_wide_2_response_next = true;
    axi_wide_2_response_id_next = dut->io_axi_ar_bits_id;
    memory.read_chunk(offset, 64, axi_wide_2_response_data);

    if (verbose) {
      log("DMEM read: addr=0x%lx instr=0x%08x\n", addr,
          axi_wide_2_response_data);
    }
  }

  // Write success response
  if (axi_wide_2_write_rsp_pending) {
    dut->io_axi_b_valid = 1;
    dut->io_axi_b_bits_id = axi_wide_2_write_b_id;
    axi_wide_2_write_rsp_pending = false;
    if (verbose) {
      log("DMEM write resp\n");
    }
  } else {
    dut->io_axi_b_valid = 0;
  }

  // Write data
  if (dut->io_axi_w_valid && axi_wide_2_write_pending) {
    auto wdata = dut->io_axi_w_bits_data;
    uint64_t strobe = (uint64_t)dut->io_axi_w_bits_strb;
    memory.write_words(axi_wide_2_write_addr, wdata, strobe, 512 / 32);
    axi_wide_2_write_rsp_pending = true;
    axi_wide_2_write_pending = false;
    axi_wide_2_write_b_id = axi_wide_2_write_rsp_id;
  }

  // Write request
  if (dut->io_axi_aw_valid) {
    axi_wide_2_write_addr = dut->io_axi_aw_bits_addr;
    axi_wide_2_write_pending = true;
    axi_wide_2_write_rsp_id = dut->io_axi_aw_bits_id;
    if (verbose) {
      log("DMEM write: addr=0x%lx\n", axi_wide_2_write_addr);
    }
  }
}

// Bootloader binary provided by cmake build process
extern unsigned char bootrom_data[];
extern unsigned int bootrom_data_len;

void Sim::load_bootrom() {
  // Load bootrom at starting address 0x1080
  memory.write_chunk(0x1080, bootrom_data_len, bootrom_data);

  // Overwrite starting address with entry point of binary
  uint32_t e = loader.get_entry_point();
  memory.write_chunk(0x1080 + bootrom_data_len - 4, 4, &e);

  if (verbose) {
    log("Finished loading program\n", e);
  }
}

int Sim::handle_host() {
  // Check for host interaction via tohost/fromhost
  size_t tohost_addr = loader.get_tohost();
  size_t fromhost_addr = loader.get_fromhost();

  uint32_t tohost = memory.read_word(tohost_addr);
  if (tohost != 0) {
    // Handle host request
    if (verbose) {
      log("Host interaction: tohost=0x%lx\n", tohost);
    }

    uint32_t syscall_mem[8];

    log("Host interaction: tohost=0x%lx\n", syscall_mem);
    for (int i = 0; i < 8; i++) {
      syscall_mem[i] = memory.read_word(tohost + i * sizeof(uint32_t));
      log("%i: %d\n", i, syscall_mem[i]);
    }

    // should match the size in htif_runtime.c
    char putc_buffer[256];

    switch (syscall_mem[0]) {
    case 64: {
      // _putchar
      memory.read_chunk(syscall_mem[2], syscall_mem[3], putc_buffer);
      printf("(hart %d) ", syscall_mem[4]);
      for (int i = 0; i < syscall_mem[3]; i++)
        printf("%c", putc_buffer[i]);
      memory.write_word(tohost_addr, 0);
      // dummy response
      memory.write_word(fromhost_addr, 1);
      break;
    }
    case 93: {
      // exit
      return 1;
      break;
    }
    default: {
      if (verbose) {
        log("Unknown host syscall mem: %d\n", syscall_mem[0]);
      }
      break;
    }
    }

    // For simplicity, we just clear the tohost value and write a response
    memory.write_word(tohost_addr, 0);
    memory.write_word(fromhost_addr, 1); // Dummy response

    if (verbose) {
      log("Host response written to fromhost=0x%lx\n", fromhost_addr);
    }
  } else {
    // log("No host interaction %x %x\n", tohost_addr, fromhost_addr);
  }
  return 0;
}

int Sim::run() {

  if (verbose) {
    fprintf(stderr, "Loading program...\n");
  }

  // Load the bootloader into memory
  load_bootrom();

  if (verbose) {
    uint32_t e = loader.get_entry_point();
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
  while (true) {
    // Handle bus interfaces before clock tick
    // handle_axi_wide();
    handle_axi_wide_2();

    // Handle host interactions
    int exit = handle_host();
    if (exit) {
      break;
    }

    // Clock tick
    tick();

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
  // trace->dump(context->time());
}

void Sim::log(const char *format, ...) {
  if (!verbose)
    return;

  va_list args;
  va_start(args, format);
  vfprintf(stderr, format, args);
  va_end(args);
}

void Sim::print_core_state() {
  if (!verbose)
    return;
}

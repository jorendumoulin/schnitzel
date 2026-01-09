#include "sim.h"
// #include "axi_interface.h"
#include "dynamic_memory.h"
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>

Sim::Sim(const std::vector<std::string> &args)
    : dut(nullptr), context(nullptr), trace(nullptr), cycle_count(0),
      memory(4096), max_cycles(0), instr_count(0), verbose(false),
      sim_finished(false) {

  init_core();
  loader.load_program(args[0], memory);

  // Add default AXI interfaces
  // add_axi_interface(std::make_unique<WideAxiInterface>("wide_axi"));
  // add_axi_interface(std::make_unique<NarrowAxiInterface>("narrow_axi"));
}

Sim::~Sim() { cleanup_core(); }

void Sim::init_core() {
  context = new VerilatedContext;
  context->commandArgs(0, (char **)nullptr);

  dut = new VTop(context);

  // Initialize signals (all default to 0 in verilator)
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
  // Reset the core
  dut->reset = 1;
  tick();
  tick();
  tick();
  tick();
  tick();
  tick();
  tick();
  dut->reset = 0;
  tick();

  cycle_count = 0;
  instr_count = 0;
  sim_finished = false;
}

// Present the response just before falling edge
void Sim::wide_mem_response() {
  dut->io_mem_rsp_valid = wide_response_pending;
  memcpy(dut->io_mem_rsp_bits_data, wide_data, 64);
}

// Execute transaction just after the falling edge
void Sim::wide_mem_transaction() {
  dut->io_mem_req_ready = 0;
  if (wide_response_pending) {
    // If not ready for response do nothing, we must stall;
    if (not dut->io_mem_rsp_ready) {
      return;
    } else { // Otherwise, the response is processed
      wide_response_pending = false;
    }
  }
  dut->io_mem_req_ready = 1;
  if (dut->io_mem_req_valid) {
    if (dut->io_mem_req_bits_wen) {
      // Execute write
      alignas(8) uint8_t current_data[64], read_data[64];
      memcpy(read_data, dut->io_mem_req_bits_wdata, 64);
      wide_strb = dut->io_mem_req_bits_ben;
      wide_addr = dut->io_mem_req_bits_addr;
      memory.read_chunk(wide_addr, 64, current_data);

      // printf("(%d) Writing data to addr %p\n", cycle_count, wide_addr);
      // printf("(%d) before:", cycle_count);
      // for (int i = 0; i < 64; i++)
      //   printf("%x ", current_data[i]);
      // printf("\n");
      //  Apply byte strobes (64 bytes total)
      for (int i = 0; i < 64; i++) {
        if (wide_strb & (1ULL << i)) {
          current_data[i] = read_data[i];
        }
      }
      // printf("(%d) after:", cycle_count);
      // for (int i = 0; i < 16; i++) {
      //   for (int j = 0; j < 4; j++) {
      //     printf("%02x", current_data[63 - (4 * i + j)]);
      //   }
      //   printf(" ");
      // }
      // printf("\n");
      memory.write_chunk(wide_addr, 64, current_data);
    } else {
      // Execute read
      wide_addr = dut->io_mem_req_bits_addr;
      memory.read_chunk(wide_addr, 64, wide_data);
    }
    wide_response_pending = true;
  }
}

void Sim::tick() {

  // Just before rising edge,
  // process axi responses
  // important to not change any values here:
  // for (auto &axi_interface : axi_interfaces) {
  //  axi_interface->handle_responses(dut, memory);
  //
  //}

  // Drive high phase
  dut->clock = 1;
  dut->eval();
  if (trace) {
    trace->dump(context->time());
  }
  context->timeInc(1);

  // Then, setup new axi transactions
  // for (auto &axi_interface : axi_interfaces) {
  //  axi_interface->handle_transactions(dut, memory);
  //}

  wide_mem_response();
  // Drive low phase
  dut->clock = 0;
  dut->eval();
  wide_mem_transaction();

  if (trace) {
    trace->dump(context->time());
  }
  context->timeInc(1);

  cycle_count++;
}

// void Sim::add_axi_interface(std::unique_ptr<AxiInterface> axi_interface) {
//   axi_interfaces.push_back(std::move(axi_interface));
// }

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
    log("Finished loading program\n");
  }
}

int Sim::handle_host() {
  // Check for host interaction via tohost/fromhost
  size_t tohost_addr = loader.get_tohost();
  size_t fromhost_addr = loader.get_fromhost();

  if (verbose) {
    printf("(%d) Looking at thost addr %p, fromhost adddr %p\n", cycle_count,
           tohost_addr, fromhost_addr);
  }

  uint32_t tohost = memory.read_word(tohost_addr);
  if (tohost != 0) {
    // Handle host request
    if (verbose) {
      printf("Host interaction: tohost=0x%x\n", tohost);
    }

    uint32_t syscall_mem[8];

    for (int i = 0; i < 8; i++) {
      syscall_mem[i] = memory.read_word(tohost + i * sizeof(uint32_t));
    }

    // should match the size in htif_runtime.c
    char putc_buffer[256];

    switch (syscall_mem[0]) {
    case 64: {
      // _putchar
      memory.read_chunk(syscall_mem[2], syscall_mem[3], putc_buffer);
      std::string a;
      for (int i = 0; i < syscall_mem[3]; i++)
        a += putc_buffer[i];
      printf("(hart %d) %s", syscall_mem[4], a.c_str());
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

#include "axi_interface.h"
#include "dynamic_memory.h"
#include <VTop.h>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <verilated.h>

AxiInterface::AxiInterface(const std::string &name, size_t data_width)
    : name(name), data_width(data_width) {}

size_t AxiInterface::get_burst_size_bytes(AxiBurstSize size) const {
  switch (size) {
  case AxiBurstSize::B1:
    return 1;
  case AxiBurstSize::B2:
    return 2;
  case AxiBurstSize::B4:
    return 4;
  case AxiBurstSize::B8:
    return 8;
  case AxiBurstSize::B16:
    return 16;
  case AxiBurstSize::B32:
    return 32;
  case AxiBurstSize::B64:
    return 64;
  case AxiBurstSize::B128:
    return 128;
  default:
    return 1;
  }
}

uint64_t AxiInterface::calculate_burst_address(uint64_t base_addr,
                                               AxiBurstType burst_type,
                                               AxiBurstSize burst_size,
                                               size_t transfer_index) const {
  size_t transfer_size = get_burst_size_bytes(burst_size);

  switch (burst_type) {
  case AxiBurstType::FIXED:
    // Address remains constant
    return base_addr;
  case AxiBurstType::INCR:
    // Incrementing address
    return base_addr + (transfer_index * transfer_size);
  case AxiBurstType::WRAP: {
    // Wrapping address - align to burst size boundary
    uint64_t wrap_boundary = calculate_wrap_boundary(base_addr, burst_size, 0);
    uint64_t offset =
        (base_addr - wrap_boundary) + (transfer_index * transfer_size);
    // For wrap bursts, the maximum wrap length is 16 * transfer_size
    // This is a limitation of the AXI protocol for wrap bursts
    uint64_t max_wrap_length = 16 * transfer_size;
    return wrap_boundary + (offset % max_wrap_length);
  }
  default:
    return base_addr;
  }
}

uint64_t AxiInterface::calculate_wrap_boundary(uint64_t addr,
                                               AxiBurstSize burst_size,
                                               uint8_t burst_len) const {
  size_t transfer_size = get_burst_size_bytes(burst_size);
  // For wrap bursts, the wrap boundary is determined by the smaller of:
  // 1. 16 transfers (AXI protocol limitation for wrap bursts)
  // 2. (burst_len + 1) transfers (actual burst length)
  size_t actual_transfers = burst_len + 1;
  size_t wrap_transfers = (actual_transfers > 16) ? 16 : actual_transfers;
  size_t wrap_length = transfer_size * wrap_transfers;

  // Wrap boundary is the address aligned to the wrap length
  // The alignment depends on the wrap length
  switch (wrap_length) {
  case 2:
    return addr & ~1ULL;
  case 4:
    return addr & ~3ULL;
  case 8:
    return addr & ~7ULL;
  case 16:
    return addr & ~15ULL;
  case 32:
    return addr & ~31ULL;
  case 64:
    return addr & ~63ULL;
  case 128:
    return addr & ~127ULL;
  case 256:
    return addr & ~255ULL;
  case 512:
    return addr & ~511ULL;
  case 1024:
    return addr & ~1023ULL;
  default:
    return addr;
  }
}

// MMIO AXI Interface Implementation
// MMIOAxiInterface::MMIOAxiInterface(const std::string &name)
//     : AxiInterface(name, 64) {}
// 
// void MMIOAxiInterface::handle_responses(VTop *dut, DynamicMemory &memory) {
//   if (dut->io_mmio_axi_r_ready and dut->io_mmio_axi_r_valid)
//     read_request.remaining_beats--;
// }
// 
// void MMIOAxiInterface::handle_transactions(VTop *dut, DynamicMemory &memory) {
//   // Handle read address channel
//   dut->io_narrow_axi_ar_ready = 1;
//   if (dut->io_mmio_axi_ar_valid) {
//     read_addr = dut->io_mmio_axi_ar_bits_addr;
//     read_id = dut->io_mmio_axi_ar_bits_id;
//     read_len = dut->io_mmio_axi_ar_bits_len;
//     read_size = static_cast<AxiBurstSize>(dut->io_mmio_axi_ar_bits_size);
//     read_burst = static_cast<AxiBurstType>(dut->io_mmio_axi_ar_bits_burst);
//     read_req_pending = true;
//     read_transfer_count = 0;
//   }
// 
//   // Handle read data channel
//   if (read_response_pending) {
//     dut->io_mmio_axi_r_valid = 1;
//     dut->io_mmio_axi_r_bits_id = response_id;
//     dut->io_mmio_axi_r_bits_resp = static_cast<uint8_t>(AxiResp::OKAY);
//     dut->io_mmio_axi_r_bits_last = (read_transfer_count >= read_len);
// 
//     // Read data from memory
//     uint64_t current_addr = calculate_burst_address(
//         read_addr, read_burst, read_size, read_transfer_count);
//     uint64_t data = 0;
//     memory.read_chunk(current_addr, sizeof(data), &data);
//     dut->io_mmio_axi_r_bits_data = data;
// 
//     if (read_transfer_count >= read_len) {
//       read_response_pending = false;
//       read_req_pending = false;
//     } else {
//       read_transfer_count++;
//     }
//   } else {
//     dut->io_mmio_axi_r_valid = 0;
//   }
// 
//   // Handle read request processing
//   if (read_req_pending && !read_response_pending) {
//     read_response_pending = true;
//     response_id = read_id;
//   }
// 
//   // Handle write address channel
//   dut->io_mmio_axi_aw_ready = 1;
//   if (dut->io_mmio_axi_aw_valid) {
//     write_addr = dut->io_mmio_axi_aw_bits_addr;
//     write_id = dut->io_mmio_axi_aw_bits_id;
//     write_len = dut->io_mmio_axi_aw_bits_len;
//     write_size = static_cast<AxiBurstSize>(dut->io_mmio_axi_aw_bits_size);
//     write_burst = static_cast<AxiBurstType>(dut->io_mmio_axi_aw_bits_burst);
//     write_addr_pending = true;
//     write_transfer_count = 0;
//   }
// 
//   // Handle write data channel
//   dut->io_mmio_axi_w_ready = 1;
//   if (dut->io_mmio_axi_w_valid) {
//     write_data = dut->io_mmio_axi_w_bits_data;
//     write_strb = dut->io_mmio_axi_w_bits_strb;
//     write_last = dut->io_mmio_axi_w_bits_last;
//     write_data_pending = true;
//   }
// 
//   // Handle write response channel
//   if (write_response_pending) {
//     dut->io_mmio_axi_b_valid = 1;
//     dut->io_mmio_axi_b_bits_id = response_id;
//     dut->io_mmio_axi_b_bits_resp = static_cast<uint8_t>(AxiResp::OKAY);
//     write_response_pending = false;
//     write_addr_pending = false;
//     write_data_pending = false;
//   } else {
//     dut->io_mmio_axi_b_valid = 0;
//   }
// 
//   // Handle write transaction processing
//   if (write_addr_pending && write_data_pending) {
//     // Write data to memory
//     uint64_t current_addr = calculate_burst_address(
//         write_addr, write_burst, write_size, write_transfer_count);
// 
//     // For narrow interface, we write 8 bytes (64 bits) at a time
//     // Apply strobe before writing
//     uint64_t current_data = 0;
//     memory.read_chunk(current_addr, sizeof(current_data), &current_data);
// 
//     // Apply byte strobes
//     for (int i = 0; i < 8; i++) {
//       if (write_strb & (1 << i)) {
//         uint8_t byte = (write_data >> (i * 8)) & 0xFF;
//         uint8_t *byte_ptr = reinterpret_cast<uint8_t *>(&current_data);
//         byte_ptr[i] = byte;
//       }
//     }
// 
//     memory.write_chunk(current_addr, sizeof(current_data), &current_data);
// 
//     if (write_last || write_transfer_count >= write_len) {
//       write_response_pending = true;
//       response_id = write_id;
//       write_addr_pending = false;
//       write_data_pending = false;
//     } else {
//       write_transfer_count++;
//       write_data_pending = false; // Wait for next data beat
//     }
//   }
// }

// Narrow AXI Interface Implementation
NarrowAxiInterface::NarrowAxiInterface(const std::string &name)
    : AxiInterface(name, 64) {}

void NarrowAxiInterface::handle_responses(VTop *dut, DynamicMemory &memory) {
  if (dut->io_narrow_axi_r_ready and dut->io_narrow_axi_r_valid)
    read_request.remaining_beats--;
}

void NarrowAxiInterface::handle_transactions(VTop *dut, DynamicMemory &memory) {
  // Handle read address channel
  dut->io_narrow_axi_ar_ready = 1;
  if (dut->io_narrow_axi_ar_valid) {
    read_addr = dut->io_narrow_axi_ar_bits_addr;
    read_id = dut->io_narrow_axi_ar_bits_id;
    read_len = dut->io_narrow_axi_ar_bits_len;
    read_size = static_cast<AxiBurstSize>(dut->io_narrow_axi_ar_bits_size);
    read_burst = static_cast<AxiBurstType>(dut->io_narrow_axi_ar_bits_burst);
    read_req_pending = true;
    read_transfer_count = 0;
  }

  // Handle read data channel
  if (read_response_pending) {
    dut->io_narrow_axi_r_valid = 1;
    dut->io_narrow_axi_r_bits_id = response_id;
    dut->io_narrow_axi_r_bits_resp = static_cast<uint8_t>(AxiResp::OKAY);
    dut->io_narrow_axi_r_bits_last = (read_transfer_count >= read_len);

    // Read data from memory
    uint64_t current_addr = calculate_burst_address(
        read_addr, read_burst, read_size, read_transfer_count);
    uint64_t data = 0;
    memory.read_chunk(current_addr, sizeof(data), &data);
    dut->io_narrow_axi_r_bits_data = data;

    if (read_transfer_count >= read_len) {
      read_response_pending = false;
      read_req_pending = false;
    } else {
      read_transfer_count++;
    }
  } else {
    dut->io_narrow_axi_r_valid = 0;
  }

  // Handle read request processing
  if (read_req_pending && !read_response_pending) {
    read_response_pending = true;
    response_id = read_id;
  }TETRA

  // Handle write address channel
  if (write_addr_pending || write_data_pending || write_response_pending) {
  dut->io_narrow_axi_aw_ready = 0;
  } else {
  dut->io_narrow_axi_aw_ready = 1;
  if (dut->io_narrow_axi_aw_valid) {
    write_addr = dut->io_narrow_axi_aw_bits_addr;
    write_id = dut->io_narrow_axi_aw_bits_id;
    write_len = dut->io_narrow_axi_aw_bits_len;
    write_size = static_cast<AxiBurstSize>(dut->io_narrow_axi_aw_bits_size);
    write_burst = static_cast<AxiBurstType>(dut->io_narrow_axi_aw_bits_burst);
    write_addr_pending = true;
    write_transfer_count = 0;
  }
  }

  // Handle write data channel
  if (write_addr_pending) {
    dut->io_narrow_axi_w_ready = 1;
    if (dut->io_narrow_axi_w_valid) {
      write_data = dut->io_narrow_axi_w_bits_data;
      write_strb = dut->io_narrow_axi_w_bits_strb;
      write_last = dut->io_narrow_axi_w_bits_last;
      write_data_pending = true;
    }
  } else {
    dut->io_narrow_axi_w_ready = 0;
  }

  // Handle write response channel
  if (write_response_pending) {
    dut->io_narrow_axi_b_valid = 1;
    dut->io_narrow_axi_b_bits_id = response_id;
    dut->io_narrow_axi_b_bits_resp = static_cast<uint8_t>(AxiResp::OKAY);
    write_response_pending = false;
    write_addr_pending = false;
    write_data_pending = false;
  } else {
    dut->io_narrow_axi_b_valid = 0;
  }

  // Handle write transaction processing
  if (write_addr_pending && write_data_pending) {
    // Write data to memory
    uint64_t current_addr = calculate_burst_address(
        write_addr, write_burst, write_size, write_transfer_count);

    // For narrow interface, we write 8 bytes (64 bits) at a time
    // Apply strobe before writing
    uint64_t current_data = 0;
    memory.read_chunk(current_addr, sizeof(current_data), &current_data);

    // Apply byte strobes
    for (int i = 0; i < 8; i++) {
      if (write_strb & (1 << i)) {
        uint8_t byte = (write_data >> (i * 8)) & 0xFF;
        uint8_t *byte_ptr = reinterpret_cast<uint8_t *>(&current_data);
        byte_ptr[i] = byte;
      }
    }

    memory.write_chunk(current_addr, sizeof(current_data), &current_data);

    if (write_last || write_transfer_count >= write_len) {
      write_response_pending = true;
      response_id = write_id;
      write_addr_pending = false;
      write_data_pending = false;
    } else {
      write_transfer_count++;
      write_data_pending = false; // Wait for next data beat
    }
  }
}

// Wide AXI Interface Implementation
WideAxiInterface::WideAxiInterface(const std::string &name)
    : AxiInterface(name, 512) {}

void WideAxiInterface::handle_responses(VTop *dut, DynamicMemory &memory) {
  if (dut->io_axi_r_ready and dut->io_axi_r_valid)
    read_request.remaining_beats--;
  // if (dut->io_axi_b_valid)
  //   assert(dut->io_axi_b_ready);
}

void WideAxiInterface::handle_transactions(VTop *dut, DynamicMemory &memory) {

  // Handle read data channel
  if (read_request.remaining_beats > 0) {
    dut->io_axi_r_valid = 1;
    dut->io_axi_r_bits_id = read_request.id;
    dut->io_axi_r_bits_resp = static_cast<uint8_t>(AxiResp::OKAY);
    dut->io_axi_r_bits_last = (read_request.remaining_beats == 1);

    // Read data from memory (64 bytes for 512-bit interface)
    uint64_t current_addr = calculate_burst_address(
        read_request.addr, read_request.burst, read_request.size,
        get_burst_size_bytes(read_request.size) - read_request.remaining_beats);

    // Use aligned storage for the data
    alignas(8) uint8_t data[64] = {0};
    memory.read_chunk(current_addr, 64, data);

    // Copy to the verilator wide data structure
    memcpy(dut->io_axi_r_bits_data, data, 64);

  } else {
    dut->io_axi_r_valid = 0;
  }

  // Handle read address channel
  if (read_request.remaining_beats == 0 and dut->io_axi_ar_valid) {
    dut->io_axi_ar_ready = 1;
    read_request.addr = dut->io_axi_ar_bits_addr;
    read_request.id = dut->io_axi_ar_bits_id;
    read_request.len = dut->io_axi_ar_bits_len;
    read_request.size = static_cast<AxiBurstSize>(dut->io_axi_ar_bits_size);
    read_request.burst = static_cast<AxiBurstType>(dut->io_axi_ar_bits_burst);
    read_request.remaining_beats = read_request.len + 1;
  } else {
    dut->io_axi_ar_ready = 0;
  }

  // Handle write response channel
  if (write_response_pending) {
    dut->io_axi_b_valid = 1;
    dut->io_axi_b_bits_id = response_id;
    dut->io_axi_b_bits_resp = static_cast<uint8_t>(AxiResp::OKAY);
    write_response_pending = false;
  } else {
    dut->io_axi_b_valid = 0;
  }

  // Handle write data channel
  if (write_request.remaining_beats > 0) {
    dut->io_axi_w_ready = 1;
    if (dut->io_axi_w_valid) {
      // Copy from the verilator wide data structure
      memcpy(write_data, dut->io_axi_w_bits_data, 64);
      write_strb = dut->io_axi_w_bits_strb;
      write_last = dut->io_axi_w_bits_last;
      // write_data_pending = true;

      uint64_t current_addr = calculate_burst_address(
          write_request.addr, write_request.burst, write_request.size,
          get_burst_size_bytes(write_request.size) -
              write_request.remaining_beats);

      alignas(8) uint8_t current_data[64];
      memory.read_chunk(current_addr, 64, current_data);

      // Apply byte strobes (64 bytes total)
      for (int i = 0; i < 64; i++) {
        if (write_strb & (1ULL << i)) {
          current_data[i] = write_data[i];
        }
      }

      memory.write_chunk(current_addr, 64, current_data);

      write_request.remaining_beats--;
      if (write_request.remaining_beats == 0) {
        assert(write_last);
        write_response_pending = true;
        response_id = write_request.id;
      }
    }
  }

  // Handle write address channel
  if (write_request.remaining_beats == 0 and dut->io_axi_aw_valid) {
    dut->io_axi_aw_ready = 1;
    write_request.addr = dut->io_axi_aw_bits_addr;
    write_request.id = dut->io_axi_aw_bits_id;
    write_request.len = dut->io_axi_aw_bits_len;
    write_request.size = static_cast<AxiBurstSize>(dut->io_axi_aw_bits_size);
    write_request.burst = static_cast<AxiBurstType>(dut->io_axi_aw_bits_burst);
    write_request.remaining_beats = write_request.len + 1;
  } else {
    dut->io_axi_aw_ready = 1;
  }
}

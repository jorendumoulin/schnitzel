#ifndef __AXI_INTERFACE_H
#define __AXI_INTERFACE_H

#include <cstddef>
#include <cstdint>
#include <string>

// Forward declarations
class VTop;
class DynamicMemory;

// Forward declaration for VlWide - we'll use void* and cast appropriately
// to avoid including verilated_types.h directly
template <size_t N_Words> struct VlWide;

/**
 * AXI Burst Types
 */
enum class AxiBurstType {
  FIXED = 0,   // Fixed address burst
  INCR = 1,    // Incrementing address burst
  WRAP = 2,    // Wrapping address burst
  RESERVED = 3 // Reserved
};

/**
 * AXI Burst Sizes (number of bytes in each transfer)
 */
enum class AxiBurstSize {
  B1 = 0,  // 1 byte
  B2 = 1,  // 2 bytes
  B4 = 2,  // 4 bytes
  B8 = 3,  // 8 bytes
  B16 = 4, // 16 bytes
  B32 = 5, // 32 bytes
  B64 = 6, // 64 bytes
  B128 = 7 // 128 bytes
};

/**
 * AXI Response Types
 */
enum class AxiResp {
  OKAY = 0,   // Normal access success
  EXOKAY = 1, // Exclusive access success
  SLVERR = 2, // Slave error
  DECERR = 3  // Decode error
};

struct AxiReq {
  size_t remaining_beats = 0;
  uint64_t addr;
  int id;
  int len;
  AxiBurstSize size;
  AxiBurstType burst;
};

/**
 * Generic AXI Interface Base Class
 *
 * This class provides a generic interface for handling AXI transactions
 * that can work with both narrow (64-bit) and wide (512-bit) AXI interfaces.
 * Supports full AXI4 protocol including burst lengths up to 256 transfers.
 */
class AxiInterface {
public:
  /**
   * Constructor
   * @param name Name of this AXI interface for logging
   * @param data_width Width of the data bus in bits (64 for narrow, 512 for
   * wide)
   */
  AxiInterface(const std::string &name, size_t data_width);

  /**
   * Virtual destructor
   */
  virtual ~AxiInterface() = default;

  /**
   * Handle AXI transactions for this interface
   * This method should be called each simulation cycle
   * after setting transactinos, sim must be evaulatued
   * before next rising edge.
   * @param dut Pointer to the verilated DUT
   * @param memory Reference to the memory system
   */
  virtual void handle_transactions(VTop *dut, DynamicMemory &memory) = 0;

  /**
   * Handle AXI transactions for this interface
   * This method should be called each simulation cycle
   * on the rising edge of the clock cycle.
   * @param dut Pointer to the verilated DUT
   * @param memory Reference to the memory system
   */
  virtual void handle_responses(VTop *dut, DynamicMemory &memory) = 0;

  /**
   * Get the name of this interface
   * @return Interface name
   */
  const std::string &get_name() const { return name; }

  /**
   * Get the data width of this interface
   * @return Data width in bits
   */
  size_t get_data_width() const { return data_width; }

protected:
  /**
   * Calculate the number of bytes in a burst transfer
   * @param size AXI burst size
   * @return Number of bytes per transfer
   */
  size_t get_burst_size_bytes(AxiBurstSize size) const;

  /**
   * Calculate the address for a burst transfer
   * @param base_addr Base address of the burst
   * @param burst_type Type of burst (FIXED, INCR, WRAP)
   * @param burst_size Size of each transfer
   * @param transfer_index Index of the current transfer in the burst
   * @return Calculated address for this transfer
   */
  uint64_t calculate_burst_address(uint64_t base_addr, AxiBurstType burst_type,
                                   AxiBurstSize burst_size,
                                   size_t transfer_index) const;

  /**
   * Calculate the wrap boundary for wrap bursts
   * @param addr Base address
   * @param burst_size Size of each transfer
   * @param burst_len Number of transfers in burst (0-255, representing 1-256
   * transfers)
   * @return Wrap boundary address
   */
  uint64_t calculate_wrap_boundary(uint64_t addr, AxiBurstSize burst_size,
                                   uint8_t burst_len) const;

  // Interface name for logging
  std::string name;

  // Data width in bits (64 for narrow, 512 for wide)
  size_t data_width;

  // Response tracking
  AxiReq read_request;
  AxiReq write_request;
  bool read_response_pending = false;
  bool write_response_pending = false;
  int response_id = 0;
};

// /**
//  * MMIO AXI Interface (64-bit data)
//  */
// class MMIOAxiInterface : public AxiInterface {
// public:
//   /**
//    * Constructor
//    * @param name Name of this AXI interface for logging
//    */
//   MMIOAxiInterface(const std::string &name);
//
//   /**
//    * Handle AXI transactions for narrow interface
//    * @param dut Pointer to the verilated DUT
//    * @param memory Reference to the memory system
//    */
//   void handle_transactions(VTop *dut, DynamicMemory &memory) override;
//
//   /**
//    * Handle AXI responses for narrow interface
//    * @param dut Pointer to the verilated DUT
//    * @param memory Reference to the memory system
//    */
//   void handle_responses(VTop *dut, DynamicMemory &memory) override;
//
// private:
//   // Read transaction state
//   bool read_req_pending = false;
//   uint64_t read_addr = 0;
//   uint8_t read_id = 0;
//   uint8_t read_len = 0;
//   AxiBurstSize read_size = AxiBurstSize::B1;
//   AxiBurstType read_burst = AxiBurstType::FIXED;
//   size_t read_transfer_count = 0;
//
//   // Write transaction state
//   bool write_addr_pending = false;
//   bool write_data_pending = false;
//   uint64_t write_addr = 0;
//   uint8_t write_id = 0;
//   uint8_t write_len = 0;
//   AxiBurstSize write_size = AxiBurstSize::B1;
//   AxiBurstType write_burst = AxiBurstType::FIXED;
//   size_t write_transfer_count = 0;
//   uint64_t write_data = 0;
//   uint8_t write_strb = 0;
//   bool write_last = false;
// };
//
//

/**
 * Narrow AXI Interface (64-bit data)
 */
class NarrowAxiInterface : public AxiInterface {
public:
  /**
   * Constructor
   * @param name Name of this AXI interface for logging
   */
  NarrowAxiInterface(const std::string &name);

  /**
   * Handle AXI transactions for narrow interface
   * @param dut Pointer to the verilated DUT
   * @param memory Reference to the memory system
   */
  void handle_transactions(VTop *dut, DynamicMemory &memory) override;

  /**
   * Handle AXI responses for narrow interface
   * @param dut Pointer to the verilated DUT
   * @param memory Reference to the memory system
   */
  void handle_responses(VTop *dut, DynamicMemory &memory) override;

private:
  // Read transaction state
  bool read_req_pending = false;
  uint64_t read_addr = 0;
  uint8_t read_id = 0;
  uint8_t read_len = 0;
  AxiBurstSize read_size = AxiBurstSize::B1;
  AxiBurstType read_burst = AxiBurstType::FIXED;
  size_t read_transfer_count = 0;

  // Write transaction state
  bool write_addr_pending = false;
  bool write_data_pending = false;
  uint64_t write_addr = 0;
  uint8_t write_id = 0;
  uint8_t write_len = 0;
  AxiBurstSize write_size = AxiBurstSize::B1;
  AxiBurstType write_burst = AxiBurstType::FIXED;
  size_t write_transfer_count = 0;
  uint64_t write_data = 0;
  uint8_t write_strb = 0;
  bool write_last = false;
};

/**
 * Wide AXI Interface (512-bit data)
 */
class WideAxiInterface : public AxiInterface {
public:
  /**
   * Constructor
   * @param name Name of this AXI interface for logging
   */
  WideAxiInterface(const std::string &name);

  /**
   * Handle AXI transactions for wide interface
   * @param dut Pointer to the verilated DUT
   * @param memory Reference to the memory system
   */
  void handle_transactions(VTop *dut, DynamicMemory &memory) override;

  /**
   * Handle AXI responses for wide interface
   * @param dut Pointer to the verilated DUT
   * @param memory Reference to the memory system
   */
  void handle_responses(VTop *dut, DynamicMemory &memory) override;

private:
  // Read transaction state
  bool read_req_pending = false;
  uint64_t read_addr = 0;
  uint8_t read_id = 0;
  uint8_t read_len = 0;
  AxiBurstSize read_size = AxiBurstSize::B1;
  AxiBurstType read_burst = AxiBurstType::FIXED;
  size_t read_transfer_count = 0;

  // Write transaction state
  bool write_addr_pending = false;
  bool write_data_pending = false;
  uint64_t write_addr = 0;
  uint8_t write_id = 0;
  uint8_t write_len = 0;
  AxiBurstSize write_size = AxiBurstSize::B1;
  AxiBurstType write_burst = AxiBurstType::FIXED;
  size_t write_transfer_count = 0;
  // Use aligned storage for VlWide<16> (512 bits = 64 bytes)
  alignas(8) uint8_t write_data[64];
  uint64_t write_strb = 0;
  bool write_last = false;
};

#endif // __AXI_INTERFACE_H

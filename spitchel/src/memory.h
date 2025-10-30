// See LICENSE for license details.

#ifndef __MEMORY_H
#define __MEMORY_H

#include <cstdint>
#include <cstring>
#include <fesvr/memif.h>
#include <vector>

/** Memory management utilities for spitchel
 *
 * This module provides helper functions for managing the simulated memory
 * system, including reading/writing different data sizes and handling
 * alignment requirements.
 */

namespace memory {

/** Memory region descriptor */
struct region_t {
  addr_t base;   // Base address
  size_t size;   // Size in bytes
  uint8_t *data; // Pointer to backing storage

  region_t(addr_t b, size_t s, uint8_t *d) : base(b), size(s), data(d) {}

  /** Check if address is within this region */
  bool contains(addr_t addr, size_t len = 1) const {
    return addr >= base && (addr + len) <= (base + size);
  }

  /** Get offset of address within this region */
  size_t offset(addr_t addr) const { return addr - base; }
};

/** Read an 8-bit value from memory
 * @param mem Memory buffer
 * @param offset Offset into buffer
 * @return Value at offset
 */
inline uint8_t read_u8(const uint8_t *mem, size_t offset) {
  return mem[offset];
}

/** Read a 16-bit value from memory (little-endian)
 * @param mem Memory buffer
 * @param offset Offset into buffer
 * @return Value at offset
 */
inline uint16_t read_u16(const uint8_t *mem, size_t offset) {
  uint16_t val;
  std::memcpy(&val, &mem[offset], sizeof(val));
  return val;
}

/** Read a 32-bit value from memory (little-endian)
 * @param mem Memory buffer
 * @param offset Offset into buffer
 * @return Value at offset
 */
inline uint32_t read_u32(const uint8_t *mem, size_t offset) {
  uint32_t val;
  std::memcpy(&val, &mem[offset], sizeof(val));
  return val;
}

/** Read a 64-bit value from memory (little-endian)
 * @param mem Memory buffer
 * @param offset Offset into buffer
 * @return Value at offset
 */
inline uint64_t read_u64(const uint8_t *mem, size_t offset) {
  uint64_t val;
  std::memcpy(&val, &mem[offset], sizeof(val));
  return val;
}

/** Write an 8-bit value to memory
 * @param mem Memory buffer
 * @param offset Offset into buffer
 * @param val Value to write
 */
inline void write_u8(uint8_t *mem, size_t offset, uint8_t val) {
  mem[offset] = val;
}

/** Write a 16-bit value to memory (little-endian)
 * @param mem Memory buffer
 * @param offset Offset into buffer
 * @param val Value to write
 */
inline void write_u16(uint8_t *mem, size_t offset, uint16_t val) {
  std::memcpy(&mem[offset], &val, sizeof(val));
}

/** Write a 32-bit value to memory (little-endian)
 * @param mem Memory buffer
 * @param offset Offset into buffer
 * @param val Value to write
 */
inline void write_u32(uint8_t *mem, size_t offset, uint32_t val) {
  std::memcpy(&mem[offset], &val, sizeof(val));
}

/** Write a 64-bit value to memory (little-endian)
 * @param mem Memory buffer
 * @param offset Offset into buffer
 * @param val Value to write
 */
inline void write_u64(uint8_t *mem, size_t offset, uint64_t val) {
  std::memcpy(&mem[offset], &val, sizeof(val));
}

/** Extract bits from a value
 * @param val Input value
 * @param hi High bit (inclusive)
 * @param lo Low bit (inclusive)
 * @return Extracted bits
 */
inline uint64_t extract_bits(uint64_t val, int hi, int lo) {
  return (val >> lo) & ((1ULL << (hi - lo + 1)) - 1);
}

/** Sign-extend a value
 * @param val Input value
 * @param bits Number of bits in input
 * @return Sign-extended value
 */
inline int64_t sign_extend(uint64_t val, int bits) {
  uint64_t sign_bit = 1ULL << (bits - 1);
  if (val & sign_bit) {
    uint64_t mask = ~((1ULL << bits) - 1);
    return val | mask;
  }
  return val;
}

/** Align address down to boundary
 * @param addr Address to align
 * @param align Alignment (must be power of 2)
 * @return Aligned address
 */
inline addr_t align_down(addr_t addr, size_t align) {
  return addr & ~(align - 1);
}

/** Align address up to boundary
 * @param addr Address to align
 * @param align Alignment (must be power of 2)
 * @return Aligned address
 */
inline addr_t align_up(addr_t addr, size_t align) {
  return (addr + align - 1) & ~(align - 1);
}

/** Check if address is aligned
 * @param addr Address to check
 * @param align Alignment (must be power of 2)
 * @return true if aligned
 */
inline bool is_aligned(addr_t addr, size_t align) {
  return (addr & (align - 1)) == 0;
}

/** Memory allocator for simulated memory regions */
class MemoryAllocator {
public:
  /** Constructor
   * @param total_size Total size of memory to manage
   */
  MemoryAllocator(size_t total_size);

  /** Destructor */
  ~MemoryAllocator();

  /** Allocate a memory region
   * @param base Base address
   * @param size Size in bytes
   * @return Pointer to allocated region, or nullptr on failure
   */
  uint8_t *allocate(addr_t base, size_t size);

  /** Get pointer to memory at address
   * @param addr Address to access
   * @return Pointer to memory, or nullptr if invalid
   */
  uint8_t *get_ptr(addr_t addr);

  /** Check if address is valid
   * @param addr Address to check
   * @param len Length of access
   * @return true if valid
   */
  bool is_valid(addr_t addr, size_t len) const;

  /** Get base address of memory */
  addr_t get_base() const { return base_addr; }

  /** Get size of memory */
  size_t get_size() const { return total_size; }

private:
  uint8_t *memory;               // Backing storage
  addr_t base_addr;              // Base address
  size_t total_size;             // Total size
  std::vector<region_t> regions; // Allocated regions
};

} // namespace memory

#endif // __MEMORY_H

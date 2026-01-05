#ifndef __DYNAMIC_MEMORY_H
#define __DYNAMIC_MEMORY_H

#include <cstddef>
#include <cstdint>
#include <map>
#include <vector>

/**
 * DynamicMemory: A memory implementation that allocates pages on-demand
 *
 * This class replaces the previous fixed-size memory allocation with a
 * dynamic approach that only allocates memory when it's actually written to.
 * Reads from unallocated regions will return zero or can be configured
 * to throw exceptions.
 */
class DynamicMemory {
public:
  /**
   * Constructor
   * @param page_size Size of each memory page in bytes (default 4KB)
   */
  DynamicMemory(size_t page_size = 4096);

  /**
   * Read a chunk of memory
   * @param addr Starting address
   * @param len Number of bytes to read
   * @param dst Destination buffer
   * @return true on success, false if accessing unmapped memory
   */
  bool read_chunk(size_t addr, size_t len, void *dst);

  /**
   * Write a chunk of memory
   * @param addr Starting address
   * @param len Number of bytes to write
   * @param src Source buffer
   */
  void write_chunk(size_t addr, size_t len, const void *src);

  /**
   * Read a 32-bit word
   * @param addr Address to read from
   * @return Value at address (0 if unmapped)
   */
  uint32_t read_word(size_t addr);

  /**
   * Write a 32-bit word
   * @param addr Address to write to
   * @param val Value to write
   */
  void write_word(size_t addr, uint32_t val);

  /**
   * Write a 32-bit word with byte strobe
   * @param addr Address to write to
   * @param val Value to write
   * @param strobe Byte enable mask (1 bit per byte)
   */
  void write_word(size_t addr, uint32_t val, uint32_t strobe);

  /**
   * Write multiple 32-bit words with strobe
   * @param addr Starting address
   * @param data Array of words to write
   * @param strobe Bitmask for byte enables (1 bit per byte)
   * @param num_words Number of words to write
   */
  void write_words(size_t addr, const uint32_t *data, uint64_t strobe,
                   size_t num_words);

  /**
   * Get the page size used by this memory instance
   * @return Page size in bytes
   */
  size_t get_page_size() const { return page_size; }

  /**
   * Check if a memory region is allocated
   * @param addr Address to check
   * @return true if the page containing addr is allocated
   */
  bool is_allocated(size_t addr) const;

  /**
   * Get total allocated memory size
   * @return Total bytes currently allocated
   */
  size_t get_allocated_size() const;

private:
  /**
   * Get or create a page for the given address
   * @param addr Any address within the desired page
   * @return Reference to the page vector
   */
  std::vector<uint8_t> &get_or_create_page(size_t addr);

  /**
   * Get a page if it exists
   * @param addr Any address within the desired page
   * @return Pointer to page vector or nullptr if not allocated
   */
  const std::vector<uint8_t> *get_page(size_t addr) const;

  // Page size in bytes
  const size_t page_size;

  // Map of page index to page data
  // Key: page index (addr / page_size)
  // Value: page data vector
  std::map<size_t, std::vector<uint8_t>> pages;
};

#endif // __DYNAMIC_MEMORY_H

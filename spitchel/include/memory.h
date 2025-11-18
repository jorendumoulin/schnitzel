#ifndef __MEMORY_H
#define __MEMORY_H

#include <cstdint>
#include <cstring>
#include <vector>

class Memory {
public:
  Memory(size_t size);

  /** Read a chunk of memory
   * @param taddr Target address
   * @param len Length to read
   * @param dst Destination buffer
   */
  void read_chunk(size_t taddr, size_t len, void *dst);

  /** Write a chunk of memory
   * @param taddr Target address
   * @param len Length to write
   * @param src Source buffer
   */
  void write_chunk(size_t taddr, size_t len, const void *src);

  uint32_t read_word(size_t addr);
  void write_word(size_t addr, uint32_t val);
  void write_word(size_t addr, uint32_t val, uint32_t strobe);

  /** Main memory storage */
  std::vector<uint8_t> mem;
};

#endif // __MEMORY_H

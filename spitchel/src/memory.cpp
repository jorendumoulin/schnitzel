#include "memory.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>

Memory::Memory(size_t size) { mem.resize(size); }

void Memory::read_chunk(size_t taddr, size_t len, void *dst) {
  if ((taddr + len) > 1024 * 1024 * 1024) {
    printf("illegal read %p %d, ignoring\n;", taddr, len);
    return;
  }
  memcpy(dst, &mem[taddr], len);
}

void Memory::write_chunk(size_t taddr, size_t len, const void *src) {
  if ((taddr + len) > 1024 * 1024 * 1024) {
    printf("illegal write, ignoring\n;");
    return;
  }
  memcpy(&mem[taddr], src, len);
}

uint32_t Memory::read_word(size_t addr) {
  uint32_t val;
  read_chunk(addr, sizeof(uint32_t), &val);
  return val;
}

void Memory::write_word(size_t addr, uint32_t data) {
  write_chunk(addr, sizeof(uint32_t), &data);
}

void Memory::write_word(size_t addr, uint32_t data, uint32_t strobe) {
  uint32_t val = read_word(addr);
  uint32_t mask = 0xFF;
  for (int i = 0; i < 4; i++) {
    if (strobe & (1 << i)) {
      uint32_t byte = (data >> (i * 8)) & 0xFF;
      val = (val & ~(mask << (i * 8))) | (byte << (i * 8));
    }
  }
  write_chunk(addr, sizeof(uint32_t), &val);
}

void Memory::write_words(size_t addr, const uint32_t *data,
                         unsigned long strobe, size_t num_words) {
  uint32_t mask = 0xFF;

  for (size_t word_index = 0; word_index < num_words; word_index++) {
    uint32_t val = read_word(addr);

    // Process each byte in the current word
    for (int i = 0; i < 4; i++) {
      if (strobe &
          (1UL << (word_index * 4 + i))) { // Check the strobe bit for this byte
        uint32_t byte = (data[word_index] >> (i * 8)) & 0xFF;
        val = (val & ~(mask << (i * 8))) | (byte << (i * 8));
      }
    }

    // Write the modified word back to memory
    write_chunk(addr, sizeof(uint32_t), &val);

    // Increment the address for the next word
    addr += sizeof(uint32_t);
  }
}

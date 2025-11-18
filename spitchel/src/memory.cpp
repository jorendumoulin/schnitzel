#include "memory.h"
#include <unistd.h>

Memory::Memory(size_t size) { mem.resize(size); }

void Memory::read_chunk(size_t taddr, size_t len, void *dst) {
  memcpy(dst, &mem[taddr], len);
}

void Memory::write_chunk(size_t taddr, size_t len, const void *src) {
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

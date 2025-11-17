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

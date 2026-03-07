#include "dynamic_memory.h"
#include <cstdio>
#include <cstring>

DynamicMemory::DynamicMemory(size_t page_size) : page_size(page_size) {}

bool DynamicMemory::read_chunk(size_t addr, size_t len, void *dst) {
  uint8_t *dst_bytes = static_cast<uint8_t *>(dst);

  for (size_t i = 0; i < len; i++) {
    size_t current_addr = addr + i;
    size_t page_index = current_addr / page_size;
    size_t offset_in_page = current_addr % page_size;

    auto it = pages.find(page_index);
    if (it != pages.end()) {
      // Page exists, read the byte
      dst_bytes[i] = it->second[offset_in_page];
    } else {
      // Page doesn't exist, return zero
      // printf("page doesn't exist :( \n");
      dst_bytes[i] = 0;
    }
    // printf("reading from addr %p page %d with offset %d data %02x\n",
    //        current_addr, page_index, offset_in_page, dst_bytes[i]);
  }

  return true;
}

void DynamicMemory::write_chunk(size_t addr, size_t len, const void *src) {
  const uint8_t *src_bytes = static_cast<const uint8_t *>(src);

  for (size_t i = 0; i < len; i++) {
    size_t current_addr = addr + i;
    size_t page_index = current_addr / page_size;
    size_t offset_in_page = current_addr % page_size;
    // if (len == 8) {
    // printf("writing to addr %p page %d with offset %d data %02x\n",
    //        current_addr, page_index, offset_in_page, src_bytes[i]);
    // }
    // Get or create the page
    auto &page = get_or_create_page(current_addr);
    page[offset_in_page] = src_bytes[i];
  }
  // printf("\n");
}

uint32_t DynamicMemory::read_word(size_t addr) {
  uint32_t val = 0;
  read_chunk(addr, sizeof(uint32_t), &val);
  return val;
}

void DynamicMemory::write_word(size_t addr, uint32_t val) {
  write_chunk(addr, sizeof(uint32_t), &val);
}

void DynamicMemory::write_word(size_t addr, uint32_t val, uint32_t strobe) {
  uint32_t current_val = read_word(addr);
  uint32_t mask = 0xFF;

  for (int i = 0; i < 4; i++) {
    if (strobe & (1 << i)) {
      uint32_t byte = (val >> (i * 8)) & 0xFF;
      current_val = (current_val & ~(mask << (i * 8))) | (byte << (i * 8));
    }
  }

  write_chunk(addr, sizeof(uint32_t), &current_val);
}

void DynamicMemory::write_words(size_t addr, const uint32_t *data,
                                uint64_t strobe, size_t num_words) {
  uint32_t mask = 0xFF;

  for (size_t word_index = 0; word_index < num_words; word_index++) {
    uint32_t current_val = read_word(addr);

    // Process each byte in the current word
    for (int i = 0; i < 4; i++) {
      if (strobe &
          (1UL << (word_index * 4 + i))) { // Check the strobe bit for this byte
        uint32_t byte = (data[word_index] >> (i * 8)) & 0xFF;
        current_val = (current_val & ~(mask << (i * 8))) | (byte << (i * 8));
      }
    }

    // Write the modified word back to memory
    write_chunk(addr, sizeof(uint32_t), &current_val);

    // Increment the address for the next word
    addr += sizeof(uint32_t);
  }
}

bool DynamicMemory::is_allocated(size_t addr) const {
  size_t page_index = addr / page_size;
  return pages.find(page_index) != pages.end();
}

size_t DynamicMemory::get_allocated_size() const {
  return pages.size() * page_size;
}

std::vector<uint8_t> &DynamicMemory::get_or_create_page(size_t addr) {
  size_t page_index = addr / page_size;

  auto it = pages.find(page_index);
  if (it == pages.end()) {
    // Page doesn't exist, create it
    auto result = pages.emplace(page_index, std::vector<uint8_t>(page_size, 0));
    return result.first->second;
  }

  return it->second;
}

const std::vector<uint8_t> *DynamicMemory::get_page(size_t addr) const {
  size_t page_index = addr / page_size;

  auto it = pages.find(page_index);
  if (it == pages.end()) {
    return nullptr;
  }

  return &it->second;
}

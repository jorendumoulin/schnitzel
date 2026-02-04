#include "loader.h"
#include "dynamic_memory.h"
#include <elfio/elfio.hpp>
#include <iostream>
#include <string>
#include <vector>

void Loader::load_program(std::string program, DynamicMemory &memory) {
  std::cout << "Loading program " << program << std::endl;
  ELFIO::elfio reader;
  if (!reader.load(program)) {
    fprintf(stderr, "Failed to load ELF program: %s\n", program.c_str());
    exit(1);
  }

  for (int i = 0; i < reader.segments.size(); ++i) {
    const ELFIO::segment *seg = reader.segments[i];

    if (seg->get_type() != ELFIO::PT_LOAD)
      continue;

    // PHYSICAL address is the LMA (Load Memory Address / Flash address)
    // VIRTUAL address is the VMA (where the code expects it to be in RAM)
    uint64_t laddr = seg->get_physical_address();
    uint64_t vaddr = seg->get_virtual_address();
    uint64_t fsize = seg->get_file_size();
    uint64_t msize = seg->get_memory_size();
    const char *data = seg->get_data();

    // 1. Load the actual data into the LOAD address (LMA)
    // This populates the "Flash" so Picolibc's memcpy has a source.
    if (fsize > 0) {
      memory.write_chunk(laddr, fsize, data);
      // printf("  Segment %d: Loaded 0x%lx bytes to LMA 0x%lx (VMA 0x%lx)\n",
      // i, fsize, laddr, vaddr);
    }

    // 2. Zero-fill the BSS at the VIRTUAL address
    // We keep this because in simulation, we want RAM ready immediately.
    // In FPGA, the crt0.s will do this again, which is safe.
    if (msize > fsize) {
      uint64_t bss_start = vaddr + fsize;
      uint64_t bss_size = msize - fsize;
      std::vector<char> zeros(bss_size, 0);
      memory.write_chunk(bss_start, bss_size, zeros.data());
    }
  }

  ELFIO::Elf_Half sec_num = reader.sections.size();
  for (int i = 0; i < sec_num; ++i) {
    ELFIO::section *psec = reader.sections[i];
    // Access to section's data
    // const char* p = reader.sections[i]->get_data()
  }
  for (int i = 0; i < sec_num; ++i) {
    ELFIO::section *psec = reader.sections[i];
    // Check section type
    if (psec->get_type() == ELFIO::SHT_SYMTAB) {
      const ELFIO::symbol_section_accessor symbols(reader, psec);
      for (unsigned int j = 0; j < symbols.get_symbols_num(); ++j) {
        std::string name;
        ELFIO::Elf64_Addr value;
        ELFIO::Elf_Xword size;
        unsigned char bind;
        unsigned char type;
        ELFIO::Elf_Half section_index;
        unsigned char other;

        // Read symbol properties
        symbols.get_symbol(j, name, value, size, bind, type, section_index,
                           other);

        if (name == "_start") {
          entry_point = value;
        } else if (name == "tohost") {
          tohost_addr = value;
        } else if (name == "fromhost") {
          fromhost_addr = value;
        }
      }
    }
  }
}

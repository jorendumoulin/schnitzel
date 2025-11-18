#include "loader.h"
#include <elfio/elfio.hpp>
#include <string>

void Loader::load_program(std::string program, Memory &memory) {
  ELFIO::elfio reader;
  if (!reader.load(program)) {
    fprintf(stderr, "Failed to load ELF program: %s\n", program.c_str());
    exit(1);
  }

  // Iterate over segments
  for (int i = 0; i < reader.segments.size(); ++i) {
    const ELFIO::segment *seg = reader.segments[i];

    if (seg->get_type() != ELFIO::PT_LOAD)
      continue; // Only loadable segments

    uint64_t vaddr = seg->get_virtual_address();
    uint64_t fsize = seg->get_file_size();   // Actual bytes in file
    uint64_t msize = seg->get_memory_size(); // Includes .bss
    const char *data = seg->get_data();      // Pointer into ELF buffer

    // Copy file-backed part
    if (fsize > 0) {
      memory.write_chunk(vaddr, fsize, data);
    } else {
      fprintf(stderr, "Warning: segment with zero file size\n");
    }

    // Zero-fill the rest (.bss)
    if (msize > fsize) {
      uint64_t bss_size = msize - fsize;
      std::vector<char> zeros(bss_size, 0);
      memory.write_chunk(vaddr + fsize, bss_size, zeros.data());
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

#include "loader.h"
#include <elfio/elfio.hpp>
#include <string>

void Loader::load_program(std::string program, Memory &memory) {
  ELFIO::elfio reader;
  printf("Loading program %s\n", program.c_str());
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

    std::cout << "Loaded segment: vaddr=0x" << std::hex << vaddr
              << " file=" << std::dec << fsize << " mem=" << msize << "\n";
  }

  ELFIO::Elf_Half sec_num = reader.sections.size();
  std::cout << "Number of sections: " << sec_num << std::endl;
  for (int i = 0; i < sec_num; ++i) {
    ELFIO::section *psec = reader.sections[i];
    std::cout << "  [" << i << "] " << psec->get_name() << "\t"
              << psec->get_size() << std::endl;
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
        std::cout << j << " " << name << " " << value << std::endl;

        if (name == "_start") {
          entry_point = value;
          std::cout << "Entry point found at 0x" << std::hex << value
                    << std::dec << "\n";
        } else if (name == "tohost") {
          tohost_addr = value;
          std::cout << "Entry point found at 0x" << std::hex << value
                    << std::dec << "\n";
        } else if (name == "fromhost") {
          fromhost_addr = value;
          std::cout << "Entry point found at 0x" << std::hex << value
                    << std::dec << "\n";
        }
      }
    }
  }
}

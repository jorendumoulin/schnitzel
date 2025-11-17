#ifndef __LOADER_H
#define __LOADER_H

#include "memory.h"
#include <string>

class Loader {
public:
  // Load a RISC-V ELF program into memory
  void load_program(std::string program, Memory &memory);

  // Get entry point address
  size_t get_entry_point() { return entry_point; };

  // Get tohost and fromhost addresses
  size_t get_tohost() { return tohost_addr; };
  size_t get_fromhost() { return fromhost_addr; };

private:
  size_t entry_point;
  size_t tohost_addr;
  size_t fromhost_addr;
};

#endif // __LOADER_H

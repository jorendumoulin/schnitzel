#include "dma/include/dma.h"
#include "memref.hh"

typedef MemRefDescriptor<uint8_t, 1> memref;

// MLIR-compiled function interfaces:
extern "C" void _mlir_ciface_memcpy_l3_l1(MemRefDescriptor<uint8_t, 1> *src,
                                          MemRefDescriptor<uint8_t, 1> *dest);

extern "C" void *dma_memcpy(void *dest, const void *src, size_t count) {

  MemRefDescriptor<uint8_t, 1> memref_src, memref_dest;
  memref_src.aligned = (unsigned char *)src;
  memref_dest.aligned = (unsigned char *)dest;
  memref_src.sizes[0] = count;
  memref_dest.sizes[0] = count;

  _mlir_ciface_memcpy_l3_l1(&memref_src, &memref_dest);

  return dest;
}

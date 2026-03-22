#include <stddef.h>
#include <stdint.h>

template <typename T, size_t N> struct MemRefDescriptor {
  T *allocated;
  T *aligned;
  intptr_t offset;
  intptr_t sizes[N];
  intptr_t strides[N];
};

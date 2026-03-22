#ifndef DMA_H
#define DMA_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * DMA-accelerated memory copy function.
 * 
 * @param dest Pointer to the destination memory location
 * @param src Pointer to the source memory location
 * @param count Number of bytes to copy
 * @return Pointer to the destination memory location
 */
void *dma_memcpy(void *dest, const void *src, size_t count);

#ifdef __cplusplus
}
#endif

#endif // DMA_H

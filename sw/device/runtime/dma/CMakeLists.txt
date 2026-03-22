add_library(dma_memcpy STATIC)
set_target_properties(dma_memcpy PROPERTIES LINKER_LANGUAGE C)
target_add_mlir_source(dma_memcpy src/dma_memcpy.mlir CONFIG "/home/joren/phd/schnitzel/generated/config.json")

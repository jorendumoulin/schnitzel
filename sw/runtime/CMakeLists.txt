# Compile and link the bootrom
enable_language(ASM)
add_executable(test sim/htif_runtime.c)
target_sources(test PRIVATE crt0.S)
target_link_options(test PRIVATE
    -nostdlib
    -nostartfiles
    -fuse-ld=lld
    -T link.ld
    -L${CMAKE_CURRENT_SOURCE_DIR}
)

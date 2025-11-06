# Compile and link the bootrom
enable_language(ASM)
add_executable(bootrom bootrom.S )
target_link_options(bootrom PRIVATE -nostdlib -nostartfiles )

# Dump bootrom as binary after building
add_custom_command(
    TARGET bootrom POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:bootrom> ${CMAKE_CURRENT_BINARY_DIR}/bootrom.bin
)

# Dump bootrom as C header file after building
add_custom_command(
    TARGET bootrom POST_BUILD
    COMMAND xxd -i -n bootrom_data ${CMAKE_CURRENT_BINARY_DIR}/bootrom.bin > ${CMAKE_CURRENT_BINARY_DIR}/bootrom.c
)

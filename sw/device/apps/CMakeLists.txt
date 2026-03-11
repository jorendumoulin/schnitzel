add_executable(hello_world.elf hello_world.c)
target_include_directories(hello_world.elf PRIVATE ${RUNTIME_PATH})
target_link_libraries(hello_world.elf PRIVATE device_runtime)

add_executable(csr_test.elf csr_test.c)
target_include_directories(csr_test.elf PRIVATE ${RUNTIME_PATH})
target_link_libraries(csr_test.elf PRIVATE device_runtime)

add_executable(dma_test.elf dma_test.c)
target_include_directories(dma_test.elf PRIVATE ${RUNTIME_PATH})
target_link_libraries(dma_test.elf PRIVATE device_runtime)

add_executable(hang.elf hang.c)
target_link_libraries(hang.elf PRIVATE device_runtime)

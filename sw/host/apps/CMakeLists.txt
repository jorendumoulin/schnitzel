add_executable(hello_world.elf hello_world.cpp)
target_link_libraries(hello_world.elf PRIVATE host_runtime)

add_executable(hello_floats.elf hello_floats.cpp)
target_link_libraries(hello_floats.elf PRIVATE host_runtime)

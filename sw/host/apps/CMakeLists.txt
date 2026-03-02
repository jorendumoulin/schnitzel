add_executable(hello_world.elf hello_world.cpp)
target_link_libraries(hello_world.elf PRIVATE host_runtime)
target_include_directories(hello_world.elf PRIVATE ${ROOT}/sw/host/runtime/)

add_executable(hello_floats.elf hello_floats.cpp)
target_link_libraries(hello_floats.elf PRIVATE host_runtime)
target_include_directories(hello_floats.elf PRIVATE ${ROOT}/sw/host/runtime/)

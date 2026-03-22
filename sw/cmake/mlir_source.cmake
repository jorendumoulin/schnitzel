# Compile an MLIR source file and add the resulting object to a target.
#
# Usage:
#   target_add_mlir_source(<target> <mlir_source> CONFIG <config_json>)
#
# Arguments:
#   target       - The CMake target to add the compiled object to
#   mlir_source  - Path to the .mlir source file
#   CONFIG       - Path to the JSON config file passed to snaxc
#
function(target_add_mlir_source target mlir_source)
  cmake_parse_arguments(MLIR "" "CONFIG" "" ${ARGN})

  if(NOT MLIR_CONFIG)
    message(FATAL_ERROR "target_add_mlir_source: CONFIG argument is required")
  endif()

  # Resolve absolute paths so generated files land in the build tree
  get_filename_component(mlir_source_abs "${mlir_source}" ABSOLUTE)
  get_filename_component(mlir_basename  "${mlir_source}" NAME_WE)

  set(out_dir "${CMAKE_CURRENT_BINARY_DIR}/mlir/${mlir_basename}")
  file(MAKE_DIRECTORY "${out_dir}")

  set(llvm_mlir_file "${out_dir}/${mlir_basename}.llvm.mlir")
  set(llvm_ir_file   "${out_dir}/${mlir_basename}.ll")
  set(obj_file       "${out_dir}/${mlir_basename}.o")

  # Step 1: snaxc — MLIR → MLIR (LLVM dialect)
  add_custom_command(
        OUTPUT  "${llvm_mlir_file}"
        COMMAND snaxc
                "${mlir_source_abs}"
                -o "${llvm_mlir_file}"
                -c "${MLIR_CONFIG}"
        DEPENDS "${mlir_source_abs}" "${MLIR_CONFIG}"
        COMMENT "snaxc: compiling ${mlir_source} -> ${llvm_mlir_file}"
        VERBATIM
    )

  # Step 2: mlir-translate — MLIR (LLVM dialect) → LLVM IR
  add_custom_command(
        OUTPUT  "${llvm_ir_file}"
        COMMAND mlir-translate
                --mlir-to-llvmir
                "${llvm_mlir_file}"
                -o "${llvm_ir_file}"
        DEPENDS "${llvm_mlir_file}"
        COMMENT "mlir-translate: ${llvm_mlir_file} -> ${llvm_ir_file}"
        VERBATIM
    )

  # Step 3: compile LLVM IR → object file (reuse the C compiler driver)
  separate_arguments(c_flags_list NATIVE_COMMAND ${CMAKE_C_FLAGS})
  add_custom_command(
        OUTPUT  "${obj_file}"
        COMMAND ${CMAKE_C_COMPILER}
                ${c_flags_list}
                -c "${llvm_ir_file}"
                -o "${obj_file}"
        DEPENDS "${llvm_ir_file}"
        COMMENT "Assembling: ${llvm_ir_file} -> ${obj_file}"
        VERBATIM
    )

  # Attach the object file to the target
  target_sources("${target}" PRIVATE "${obj_file}")

  # Make sure the target itself depends on the custom commands
  set_source_files_properties("${obj_file}" PROPERTIES GENERATED TRUE)

endfunction()

#include "model_data.h"
#include <executorch/extension/data_loader/buffer_data_loader.h>
#include <executorch/runtime/core/data_loader.h>
#include <executorch/runtime/executor/memory_manager.h>
#include <executorch/runtime/executor/method.h>
#include <executorch/runtime/executor/program.h>
#include <executorch/runtime/kernel/operator_registry.h>
#include <executorch/runtime/platform/platform.h>
#include <executorch/runtime/platform/runtime.h>
#include <htif_runtime.h>
#include <stdio.h>

using executorch::aten::Tensor;
using executorch::aten::TensorImpl;
using ScalarType = executorch::runtime::etensor::ScalarType;
using namespace executorch::runtime;
using namespace executorch::extension;
using executorch::runtime::runtime_init;

// 1. Memory for the method's internal state (metadata, tensors)
uint8_t method_allocator_pool[10 * 1024];
uint8_t activation_pool[10 * 1024];

int main() {
  et_pal_init();
  runtime_init();
  // register_all_kernels();

  if (registry_has_op_function("aten::add.out")) {
    printf("aten::add.out present\n");
  } else {
    printf("aten::add.out not present\n");
  }
  if (registry_has_op_function("my_ops::mul3.out")) {
    printf("my_ops::mul3.out present\n");
  } else {
    printf("my_ops::mul3.out not present\n");
  }

  if (model_pte == nullptr || model_pte_len == 0) {
    printf("Error: Model buffer is empty!\n");
    return -1;
  }

  BufferDataLoader loader(model_pte, model_pte_len);

  // Check if Program loaded correctly
  auto program_res = Program::load(&loader);
  if (!program_res.ok()) {
    printf("Program load failed: 0x%x\n", (unsigned int)program_res.error());
    return -1;
  }
  Program &program = program_res.get(); // Use .get() to access the object
  //

  MemoryAllocator method_allocator(sizeof(method_allocator_pool),
                                   method_allocator_pool);

  printf("Allocater info:\n");
  printf("Size: %d\n", method_allocator.size());
  printf("Size: %p\n", method_allocator.base_address());

  // Get method count and names
  printf("Program info:\n");
  printf("   Method count: %zu\n", program.num_methods());

  auto method_name_result = program.get_method_name(0);
  if (!method_name_result.ok()) {
    printf("Failed to get method name: error %d\n",
           (int)method_name_result.error());
  }

  printf("   Method 0 name: %s\n", *method_name_result);

  Span<uint8_t> memory_planned_buffers[1]{
      {activation_pool, sizeof(activation_pool)}};
  HierarchicalAllocator planned_memory({memory_planned_buffers, 1});
  MemoryManager memory_manager(&method_allocator, &planned_memory);

  printf("Running load_method...\n");
  // Check if Method loaded correctly
  auto method_res = program.load_method("forward", &memory_manager);
  if (!method_res.ok()) {
    printf("Method load failed: 0x%x\n", (unsigned int)method_res.error());
    return -1;
  }

  printf("Running method_res...\n");
  Method &method = method_res.get();

  // Create input tensor: [1, 28, 28]
  TensorImpl::SizesType input_sizes[1] = {10};
  TensorImpl::DimOrderType dim_order[3] = {0};
  float input_data[10] = {1.0,  0.5, 3.2,   5.6,   2.1,
                          -3.4, 0.7, -0.13, -0.88, 0.22};

  TensorImpl input_impl(ScalarType::Float,
                        1,           // 3 dimensions: [batch, height, width]
                        input_sizes, // [1, 28, 28]
                        input_data, dim_order);
  Tensor input(&input_impl);

  printf("Setting input...\n");

  auto abc = method.set_input(&input, 0);

  printf("Running inference...\n");
  Error err = method.execute();

  if (err != Error::Ok) {
    printf("Execution failed: 0x%x\n", (unsigned int)err);
    return -1;
  }

  printf("Success!\n");
  float *output_data =
      method.get_output(0).toTensor().mutable_data_ptr<float>();
  printf("Result: {%f, %f, %f}\n", output_data[0], output_data[1],
         output_data[2]);
  htif_exit(0);
  return 0;
}

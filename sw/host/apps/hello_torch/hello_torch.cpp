#include "model3_data.h"
#include <executorch/extension/data_loader/buffer_data_loader.h>
#include <executorch/runtime/core/data_loader.h>
#include <executorch/runtime/executor/memory_manager.h>
#include <executorch/runtime/executor/method.h>
#include <executorch/runtime/executor/program.h>
#include <executorch/runtime/kernel/operator_registry.h>
#include <executorch/runtime/platform/platform.h>
#include <executorch/runtime/platform/runtime.h>

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

  if (model3_pte == nullptr || model3_pte_len == 0) {
    printf("Error: Model buffer is empty!\n");
    return -1;
  }

  BufferDataLoader loader(model3_pte, model3_pte_len);

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
  printf("Running method_res for sure now!\n");
  Method &method = method_res.get();

  // Create input tensor: [1, 28, 28]
  TensorImpl::SizesType input_sizes[1] = {1};
  TensorImpl::DimOrderType dim_order[3] = {0};
  float input_data[1] = {3.14};

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
  printf("Result: %f\n", output_data[0]);
  return 0;
}

#include <memref.hh>
#include <runtime.h>
#include <stdint.h>

// Testing code to just call the compiled gemm operator
//
extern "C" void _mlir_ciface_gemm(MemRefDescriptor<int32_t, 2> result,
                                  MemRefDescriptor<int8_t, 2> a,
                                  MemRefDescriptor<int8_t, 2> b);

#ifndef GEMM_M
#define GEMM_M 16
#endif

#ifndef GEMM_N
#define GEMM_N 16
#endif

#ifndef GEMM_K
#define GEMM_K 16
#endif

int8_t a_data[GEMM_M * GEMM_K];
MemRefDescriptor<int8_t, 2> a = {
    a_data, a_data, 0, {GEMM_M, GEMM_K}, {GEMM_K, 1}};

int8_t b_data[GEMM_K * GEMM_N];
MemRefDescriptor<int8_t, 2> b = {
    b_data, b_data, 0, {GEMM_K, GEMM_N}, {GEMM_N, 1}};

int32_t result_data[GEMM_M * GEMM_N];
MemRefDescriptor<int32_t, 2> result = {
    result_data, result_data, 0, {GEMM_M, GEMM_N}, {GEMM_N, 1}};

// Variables to reference from python:
extern "C" int8_t *gemm_a_data = a.aligned;
extern "C" int8_t *gemm_b_data = b.aligned;
extern "C" int32_t *gemm_d_data = result.aligned;

int main() {
  _mlir_ciface_gemm(result, a, b);
  htif_exit(0);
}

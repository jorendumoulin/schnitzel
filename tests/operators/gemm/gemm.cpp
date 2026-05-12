#include <memref.hh>
#include <runtime.h>
#include <stdalign.h>
#include <stdint.h>

// Testing code to just call the compiled gemm operator
//
extern "C" void _mlir_ciface_gemm(MemRefDescriptor<int32_t, 2> *result,
                                  MemRefDescriptor<int8_t, 2> *a,
                                  MemRefDescriptor<int8_t, 2> *b);

#ifndef GEMM_M
#define GEMM_M 16
#endif

#ifndef GEMM_N
#define GEMM_N 16
#endif

#ifndef GEMM_K
#define GEMM_K 16
#endif

alignas(64) int8_t a_data[GEMM_M * GEMM_K] = {0};
MemRefDescriptor<int8_t, 2> a = {
    a_data, a_data, 0, {GEMM_M, GEMM_K}, {GEMM_K, 1}};

alignas(64) int8_t b_data[GEMM_K * GEMM_N];
MemRefDescriptor<int8_t, 2> b = {
    b_data, b_data, 0, {GEMM_K, GEMM_N}, {GEMM_N, 1}};

MemRefDescriptor<int32_t, 2> result;

int main() {
  _mlir_ciface_gemm(&result, &a, &b);
  cluster_sync();
  htif_exit(0);
}

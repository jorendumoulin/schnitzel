#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

// --- CSR ACCESS UTILITIES ---

static inline uintptr_t read_mstatus() {
  uintptr_t val;
  asm volatile("csrr %0, mstatus" : "=r"(val));
  return val;
}

static inline uintptr_t read_sstatus() {
  uintptr_t val;
  asm volatile("csrr %0, sstatus" : "=r"(val));
  return val;
}

// --- CORE LOGIC ---

void print_fpu_state(const char *label) {
  uintptr_t ms = read_mstatus();
  int fs = (ms >> 13) & 0x3;
  const char *states[] = {"00 (Off)", "01 (Initial)", "10 (Clean)",
                          "11 (Dirty)"};

  printf("[%s] mstatus: 0x%lx | FS Bits: %s\n", label, (unsigned long)ms,
         states[fs]);
}

bool force_enable_fpu() {
  printf("[Action] Attempting FPU Ignition...\n");

  // We target both mstatus and sstatus to cover all privilege bases.
  // fscsr x0 is the critical 'handshake' with the FP hardware.
  asm volatile("li t0, 0x6000\n"
               "csrs mstatus, t0\n"
               "csrs sstatus, t0\n"
               "fscsr x0\n"
               :
               :
               : "t0", "memory");

  uintptr_t ms = read_mstatus();
  return ((ms >> 13) & 0x3) != 0;
}

void run_math_tests() {
  printf("\n--- Starting Hardware Math Tests ---\n");

  // Use volatile to force actual hardware instructions (prevent compiler
  // optimization)
  volatile float f1 = 12.5f;
  volatile float f2 = 0.5f;
  volatile double d1 = 1.23456789;
  volatile double d2 = 2.0;

  // Test 1: Simple Addition/Subtraction
  float res_add = f1 + f2;
  printf("  [1] Addition (12.5 + 0.5):    %d.%01d (Expected 13.0)\n",
         (int)res_add, (int)((res_add - (int)res_add) * 10));

  // Test 2: Multiplication/Division
  float res_div = f1 / f2;
  printf("  [2] Division (12.5 / 0.5):    %d.%01d (Expected 25.0)\n",
         (int)res_div, (int)((res_div - (int)res_div) * 10));

  // Test 3: Double Precision (D-Extension)
  double res_dbl = d1 * d2;
  printf("  [3] Double Multi:             %d.%03d (Expected 2.469)\n",
         (int)res_dbl, (int)((res_dbl - (int)res_dbl) * 1000));

  // Test 4: Comparison (Triggers __netf2 or fcmp)
  if (f1 > f2) {
    printf("  [4] Comparison:               PASSED\n");
  } else {
    printf("  [4] Comparison:               FAILED\n");
  }

  // Test 5: Float-to-Int Conversion
  int32_t i_val = (int32_t)f1;
  if (i_val == 12) {
    printf("  [5] Conversion:               PASSED\n");
  } else {
    printf("  [5] Conversion:               FAILED\n");
  }
}

int main() {
  printf("========================================\n");
  printf("   RISC-V CVA6 FPU DIAGNOSTIC TOOL      \n");
  printf("========================================\n");

  print_fpu_state("Pre-Enable");

  if (!force_enable_fpu()) {
    printf("\nERROR: FPU could not be enabled. Hardware may not exist or "
           "privilege is too low.\n");
    return 1;
  }

  print_fpu_state("Post-Enable");

  run_math_tests();

  printf("\nConclusion: All floating point tests completed.\n");
  printf("========================================\n");

  return 0;
}

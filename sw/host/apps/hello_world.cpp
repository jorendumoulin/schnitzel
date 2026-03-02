#include <cstdio>
#include <runtime.h>

int main() {
  for (int i = 0; i < 3; i++) {
    printf("Hello World! %d\n", i);
  }
  global_sync();
  return 0;
}

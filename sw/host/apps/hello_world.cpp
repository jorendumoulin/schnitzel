#include <cstdio>
#include <runtime.h>

int main() {
  for (int i = 0; i < 10; i++) {
    printf("Hello World! %d\n", i);
  }
  sync_global();
  return 0;
}

#include <runtime.h>

int main() {

  int hart = hart_id();

  global_sync();
  if (hart == 1) {
    for (int i = 0; i < 3; i++) {
      printf("Hello World! %d\n", i);
    }
  }
  cluster_sync();
  if (hart == 2) {
    for (int i = 0; i < 3; i++) {
      printf("Hello World! %d\n", i);
    }
  }
  cluster_sync();

  // Exit with code 0
  htif_exit(0);
  return 0;
}

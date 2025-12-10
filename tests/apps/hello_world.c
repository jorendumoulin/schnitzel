#include <runtime.h>

int main() {

    int hart = hartid();

    for(int i = 0; i < 100; i++) {
        printf("Hello World! %d\n", i);
    }

    // Exit with code 0
    htif_exit(0);
    return 0;
}

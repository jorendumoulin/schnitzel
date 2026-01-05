host.elf:
	clang -O0 host.c --target=riscv64-unknown-elf -march=rv64gc -mabi=lp64d -nostdlib -nostartfiles -fuse-ld=/usr/bin/ld.lld -T link.ld -o host.elf

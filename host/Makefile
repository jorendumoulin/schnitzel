host.elf:
	clang -O3 host.c crt0.S --target=riscv64-unknown-elf -march=rv64gc_zicbom -mabi=lp64d -nostdlib -mcmodel=medany -nostartfiles -fuse-ld=/usr/bin/ld.lld -T link.ld -o host.elf



.global _start
_start:
    csrr  a0, mhartid
    la    a1, device_tree
    lw    t0, entry_addr
    jalr  t0
no_payload:
    wfi
    j     no_payload
entry_addr:
    .word no_payload
device_tree:

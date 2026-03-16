from collections.abc import Callable

from snaxc.hw.acc_context import *
from snaxc.hw.accelerator import Accelerator


def get_all_accelerators() -> dict[str, Callable[[], type[Accelerator]]]:
    """Return all available accelerator types"""

    def get_snax_alu():
        from snaxc.hw.snax_alu import SNAXAluAccelerator

        return SNAXAluAccelerator

    def get_xdma():
        from snaxc.hw.snax_xdma import SNAXXDMAAccelerator

        return SNAXXDMAAccelerator

    return {
        "alu": get_snax_alu,
        "dma": get_xdma,
    }

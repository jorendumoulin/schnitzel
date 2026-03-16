from collections.abc import Callable

from snaxc.hw.acc_context import *
from snaxc.hw.accelerator import Accelerator


def get_all_accelerators() -> dict[str, Callable[[], type[Accelerator]]]:
    """Return all available accelerator types"""

    def get_alu():
        from snaxc.hw.accelerators.alu import Alu

        return Alu

    def get_dma():
        from snaxc.hw.accelerators.dma import Dma

        return Dma

    return {
        "alu": get_alu,
        "dma": get_dma,
    }

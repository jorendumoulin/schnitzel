from dataclasses import dataclass

from xdsl.dialects.builtin import StringAttr

from snaxc.hw.accelerator import Accelerator


@dataclass
class Memory:
    name: str
    """Name of the memory"""

    start: int
    """Memory starting address"""

    size: int
    """Memory capacity in bytes"""

    @property
    def attribute(self) -> StringAttr:
        """MLIR memory space attribute"""
        return StringAttr(self.name)


@dataclass
class Core:
    hart_id: int
    accelerators: list[Accelerator]


@dataclass
class Cluster:
    memory: Memory
    cores: list[Core]


@dataclass
class System:
    memory: Memory
    clusters: list[Cluster]

from dataclasses import dataclass
from typing import Iterable

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

    def iter_mems(self) -> Iterable[Memory]:
        yield self.memory
        for cluster in self.clusters:
            yield cluster.memory

    def iter_accelerators(self) -> Iterable[Accelerator]:
        for cluster in self.clusters:
            for core in cluster.cores:
                yield from core.accelerators

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


class AcceleratorConfig(ABC): ...


class EmptyAcceleratorConfig(AcceleratorConfig): ...


class AcceleratorWrapper(ABC):
    @abstractmethod
    def get_config(self) -> AcceleratorConfig: ...


@dataclass
class AluWrapper(AcceleratorWrapper):
    type: Literal["alu"]
    config: EmptyAcceleratorConfig

    def get_config(self):
        return self.config


@dataclass
class DmaWrapper:
    type: Literal["dma"]
    config: EmptyAcceleratorConfig

    def get_config(self):
        return self.config


Accelerator = AluWrapper | DmaWrapper


@dataclass
class SnaxMemoryConfig:
    name: str
    start: int
    size: int


@dataclass
class CoreConfig:
    hart_id: int
    accelerators: list[AluWrapper | DmaWrapper]


@dataclass
class ClusterConfig:
    memory: SnaxMemoryConfig
    cores: list[CoreConfig]


@dataclass
class SystemConfig:
    memory: SnaxMemoryConfig
    clusters: list[ClusterConfig]

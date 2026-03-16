from typing import Any

from dacite import from_dict
from dacite.config import Config as DaciteConfig

from snaxc.hw import get_all_accelerators
from snaxc.hw.system import System, Accelerator


def parse_config(config: Any) -> System:
    system = from_dict(
        System,
        config,
        DaciteConfig(type_hooks={Accelerator: lambda accelerator: get_all_accelerators()[accelerator["type"]]()()}),
    )
    system.resolve_parents()
    return system

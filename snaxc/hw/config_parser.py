from typing import Any

from dacite import from_dict
from dacite.config import Config as DaciteConfig

from snaxc.hw import get_all_accelerators
from snaxc.hw.accelerator import Accelerator
from snaxc.hw.system import System


def parse_config(config: Any) -> System:
    system = from_dict(
        System,
        config,
        DaciteConfig(type_hooks={Accelerator: lambda accelerator: get_all_accelerators()[accelerator["type"]]()()}),
    )
    return system

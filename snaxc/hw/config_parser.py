from typing import Any

from dacite import from_dict
from dacite.config import Config as DaciteConfig

from snaxc.hw import get_all_accelerators
from snaxc.hw.system import Accelerator, System


def _parse_accelerator(accelerator: dict[str, Any]) -> Accelerator:
    acc_type = accelerator["type"]
    if acc_type == "phs":
        from snaxc.hw.accelerators.phs import Phs

        return Phs.from_config(accelerator)
    return get_all_accelerators()[acc_type]()()


def parse_config(config: Any) -> System:
    system = from_dict(
        System,
        config,
        DaciteConfig(type_hooks={Accelerator: _parse_accelerator}),
    )
    system.resolve_parents()
    return system

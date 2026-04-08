import argparse
import json
from collections.abc import Sequence

from xdsl.dialects import get_all_dialects
from xdsl.transforms import get_all_passes
from xdsl.xdsl_opt_main import xDSLOptMain

from snaxc.dialects import get_all_snax_dialects
from snaxc.hw.acc_context import AccContext
from snaxc.hw.config_parser import parse_config
from snaxc.transforms import get_all_snax_passes

# Default system config matching the schnitzel architecture
DEFAULT_SYSTEM_CONFIG = {
    "memory": {"name": "L3", "start": 0x2_0000_0000, "size": 0x2_0000_0000},
    "clusters": [
        {
            "memory": {"name": "L1", "start": 0x1_0000_0000, "size": 0x1_0000},
            "cores": [
                {"hart_id": 1, "accelerators": []},
                {"hart_id": 2, "accelerators": []},
            ],
        }
    ],
}


class SNAXOptMain(xDSLOptMain):
    def __init__(
        self,
        description: str = "SNAX modular optimizer driver",
        args: Sequence[str] | None = None,
    ):
        self.available_frontends = {}
        self.available_passes = {}
        self.available_targets = {}

        self.ctx: AccContext = AccContext()

        self.register_all_dialects()
        self.register_all_frontends()
        self.register_all_passes()
        self.register_all_targets()

        # arg handling
        arg_parser = argparse.ArgumentParser(description=description)
        self.register_all_arguments(arg_parser)
        arg_parser.add_argument(
            "--system-config",
            type=str,
            default=None,
            help="path to the system configuration JSON file (default: built-in schnitzel config)",
        )
        self.args = arg_parser.parse_args(args=args)
        self.ctx.allow_unregistered = self.args.allow_unregistered_dialect

        self.load_system_config()
        self.setup_pipeline()

    def load_system_config(self):
        if self.args.system_config is not None:
            with open(self.args.system_config) as f:
                config = json.load(f)
        else:
            config = DEFAULT_SYSTEM_CONFIG
        self.ctx.system = parse_config(config)

    def register_all_dialects(self):
        all_dialects = get_all_dialects()
        # FIXME: override upstream accfg and stream dialect.
        all_dialects.pop("accfg", None)
        all_dialects.pop("stream", None)
        all_dialects.update(get_all_snax_dialects())
        for dialect_name, dialect_factory in all_dialects.items():
            self.ctx.register_dialect(dialect_name, dialect_factory)

    def register_all_passes(self):
        """
        Register all SNAX and xDSL passes
        """
        all_passes = get_all_passes()
        all_passes.update(get_all_snax_passes())
        for pass_name, pass_factory in all_passes.items():
            self.register_pass(pass_name, pass_factory)


def main():
    SNAXOptMain().run()


if "__main__" == __name__:
    main()

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np


class Simulator:
    _lib: ModuleType

    def __init__(self):
        self.load_lib()

    def test(self) -> int:
        sim = self._lib.Sim(
            [
                "/home/joren/phd/schnitzel/build/device/apps/hello_world.elf",
                "/home/joren/phd/schnitzel/build/host/apps/hello_world.elf",
            ]
        )
        symbols = sim.get_symbols()
        addr: int = symbols["hello_world_var"]
        existing = sim.read_data(addr, 40)
        print(np.frombuffer(existing, dtype=np.int32))
        data = np.array(range(24, 34), dtype=np.int32)
        sim.write_data(addr, data.tobytes())
        return sim.run()

    def load_lib(self) -> None:
        lib_path = self._find_lib()
        if not lib_path:
            raise RuntimeError(
                "Could not find libsim_c_api. Make sure to build the project with CMake first: cmake --build build"
            )

        spec = importlib.util.spec_from_file_location("my_module", lib_path)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self._lib = module

    def _find_lib(self) -> Path | None:
        path = Path(__file__).resolve().parent.parent / "build" / "sim" / "my_module.cpython-312-x86_64-linux-gnu.so"
        if path.exists():
            return path

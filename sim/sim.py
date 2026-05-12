import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Sequence

import numpy as np


class Simulator:
    _lib: ModuleType

    def __init__(
        self,
        elf_paths: list[str | Path] | None = None,
        lib_path: str | Path | None = None,
        vlt_args: str | list[str] = "",
    ):
        self.load_lib(lib_path)
        self._elfs = [str(p) for p in (elf_paths or [])]
        self._vlt_args = vlt_args if isinstance(vlt_args, str) else " ".join(vlt_args)
        self._sim = None

    def sim(self):
        if self._sim is None:
            if not self._elfs:
                raise RuntimeError("No ELF paths provided")
            self._sim = self._lib.Sim(self._elfs, self._vlt_args)
        return self._sim

    def get_symbols(self) -> dict[str, int]:
        return self.sim().get_symbols()

    def write_data(self, addr: int, data: bytes) -> None:
        self.sim().write_data(addr, data)

    def read_data(self, addr: int, size: int) -> bytes:
        return self.sim().read_data(addr, size)

    def run(self) -> int:
        return self.sim().run()

    def test(self) -> int:
        # Smoke test — retained for backward compatibility, hardcoded paths.
        sim = self._lib.Sim(
            [
                "/home/joren/phd/schnitzel/tests/operators/gemm/build/gemm",
            ]
        )
        symbols = sim.get_symbols()
        addr: int = symbols["hello_world_var"]
        existing = sim.read_data(addr, 40)
        print(np.frombuffer(existing, dtype=np.int32))
        data = np.array(range(24, 34), dtype=np.int32)
        sim.write_data(addr, data.tobytes())
        return sim.run()

    def load_lib(self, lib_path: str | Path | None) -> None:
        path = Path(lib_path) if lib_path else self._find_lib()
        if not path or not path.exists():
            raise RuntimeError(
                "Could not find simulator pybind module (my_module.cpython-*.so). "
                "Build with cmake first, or pass lib_path explicitly."
            )
        spec = importlib.util.spec_from_file_location("my_module", path)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self._lib = module

    def _find_lib(self) -> Path | None:
        repo_root = Path(__file__).resolve().parent.parent
        for candidate_dir in (repo_root / "build" / "sim", repo_root):
            matches = sorted(candidate_dir.glob("my_module.cpython-*.so"))
            if matches:
                return matches[0]
        return None

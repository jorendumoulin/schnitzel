from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Self

import numpy as np
from xdsl.ir import Operation
from xdsl.ir.affine import AffineDimExpr, AffineMap

from snaxc.hw.streamers.streamers import Streamer
from snaxc.hw.system import Accelerator
from snaxc.ir.dart.access_pattern import Schedule, SchedulePattern, Template, TemplatePattern
from snaxc.ir.dart.affine_transform import AffineTransform


@dataclass
class TensorCore(Accelerator):
    """
    Accelerator interface class for the ALU.
    """

    name = "tensorcore"
    m: int
    n: int
    k: int
    a: Streamer
    b: Streamer
    c: Streamer

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> Self:
        m = params["M"]
        n = params["N"]
        k = params["K"]
        a = Streamer.from_params(params["a"], "a")
        b = Streamer.from_params(params["b"], "b")
        c = Streamer.from_params(params["c"], "c")
        return cls(m, n, k, a, b, c)

    @property
    def streamers(self) -> Sequence[Streamer]:
        return (self.a, self.b, self.c)

    def launch_param(self) -> str:
        return "start"

    def param_values(self) -> dict[str, int]:
        base = 0x900
        csrs: list[str] = []
        for streamer in self.streamers:
            csrs.append(streamer.addr_params())
            csrs.extend(streamer.ts_params())
            csrs.extend(streamer.ub_params())
            csrs.extend(streamer.ss_params())
        csrs.append(self.launch_param())
        return {param: base + idx for idx, param in enumerate(csrs)}

    def barrier_address(self) -> int:
        return self.param_values()[self.launch_param()]

    # Dart Template For Scheduler
    def get_template(self, op: Operation) -> Template:
        m, n, k = (AffineDimExpr(i) for i in range(3))
        template = [
            AffineMap(3, 0, (m, k)),
            AffineMap(3, 0, (k, n)),
            AffineMap(3, 0, (m, n)),
        ]
        template_bounds = (self.m, self.n, self.k)
        return Template(TemplatePattern(template_bounds, tp) for tp in template)

    # Transform the schedule to match with the way data is accessed in the accelerator:
    def transform_schedule(self, sched: Schedule) -> Schedule:
        # second op takes in data still in row-major
        arr = np.copy(sched[1].pattern.A)
        arr[:, [-1, -2]] = arr[:, [-2, -1]]
        return Schedule(
            [
                sched[0],
                SchedulePattern(sched[1].bounds, AffineTransform(arr, sched[1].pattern.b)),
                sched[2],
            ]
        )

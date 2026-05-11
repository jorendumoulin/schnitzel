from dataclasses import dataclass

import numpy as np
from xdsl.ir import Operation
from xdsl.ir.affine import AffineDimExpr, AffineMap

from snaxc.hw.streamers.streamers import Streamer, StreamerConfiguration
from snaxc.hw.system import Accelerator
from snaxc.ir.dart.access_pattern import Schedule, SchedulePattern, Template, TemplatePattern
from snaxc.ir.dart.affine_transform import AffineTransform


@dataclass
class TensorCore(Accelerator):
    """
    Accelerator interface class for the ALU.
    """

    name = "tensorcore"
    streamers = StreamerConfiguration(
        [
            Streamer(4, 6, (4,), "a"),
            Streamer(4, 6, (4,), "b"),
            Streamer(4, 6, (4, 4), "c"),
        ]
    )

    def launch_param(self) -> str:
        return "start"

    def param_values(self) -> dict[str, int]:
        base = 0x900
        csrs: list[str] = []
        for streamer in self.streamers.streamers:
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
        template_bounds = (4, 4, 4)
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

from dataclasses import dataclass, field
from typing import Iterable, Optional

from xdsl.dialects.builtin import StringAttr

from abc import ABC
from collections.abc import Sequence

from xdsl.ir import Operation

from snaxc.dialects import accfg


class Accelerator(ABC):
    name: str
    _core: Optional["Core"] = field(default=None, init=False, repr=False)

    def resolve_parents(self, core: "Core"):
        self._core = core

    def convert_to_acc_ops(self, op: Operation) -> Sequence[Operation]:
        """
        Lowers the operation op to a sequence of acc_ops.
        acc_ops are:
            - *.op that generates SSAValues consumed by accfg.setup
            - accfg.setup
            - accfg.launch
            - accfg.await
        These ops can further be lowered by specific instances of the
        Accelerator interface
        """
        raise NotImplementedError()

    def generate_acc_op(self) -> accfg.AcceleratorOp:
        """
        Return an accelerator op:

        "accfg.accelerator"() <{
            name            = @name_of_the_accelerator,
            fields          = {field_1=address_1, field_2=address2},
            launch_fields   = {launch_field_1=address_1,
            barrier         = barrier_address,
        }> : () -> ()
        """
        raise NotImplementedError()

    @staticmethod
    def lower_acc_await(acc_op: accfg.AcceleratorOp) -> Sequence[Operation]:
        """
        Based on the accfg.accelerator op, return the necessary sequence of
        lower-level operations to perform
        asynchronous await on the accelerator.
        """
        raise NotImplementedError()

    def lower_acc_launch(self, launch_op: accfg.LaunchOp, acc_op: accfg.AcceleratorOp) -> Sequence[Operation]:
        """
        Based on the accfg.accelerator op, return the necessary sequence of
        lower-level operations to perform an
        asynchronous launch of the accelerator.
        """
        raise NotImplementedError()

    @staticmethod
    def lower_acc_setup(setup_op: accfg.SetupOp, acc_op: accfg.AcceleratorOp) -> Sequence[Operation]:
        """
        Based on the accfg.accelerator op and the accfg.SetupOp,
        return the necessary sequence of lower-level operations to perform
        accelerator configuration.
        """
        raise NotImplementedError()


@dataclass
class Memory:
    name: str
    """Name of the memory"""

    start: int
    """Memory starting address"""

    size: int
    """Memory capacity in bytes"""

    _parent: Optional["Cluster | System"] = field(default=None, init=False, repr=False)

    @property
    def attribute(self) -> StringAttr:
        """MLIR memory space attribute"""
        return StringAttr(self.name)

    @property
    def parent(self) -> "Cluster | System":
        assert self._parent is not None
        return self._parent

    def resolve_parents(self, parent: "Cluster | System"):
        self._parent = parent


@dataclass
class Core:
    hart_id: int
    accelerators: list[Accelerator]
    _cluster: Optional["Cluster"] = field(default=None, init=False, repr=False)

    def resolve_parents(self, cluster: "Cluster"):
        self._cluster = cluster
        for accelerator in self.accelerators:
            accelerator.resolve_parents(self)


@dataclass
class Cluster:
    memory: Memory
    cores: list[Core]
    _system: Optional["System"] = field(default=None, init=False, repr=False)

    @property
    def system(self) -> "System":
        assert self._system is not None
        return self._system

    def resolve_parents(self, parent: "System"):
        self._system = parent
        self.memory.resolve_parents(self)
        for core in self.cores:
            core.resolve_parents(self)


@dataclass
class System:
    memory: Memory
    clusters: list[Cluster]

    def resolve_parents(self):
        self.memory.resolve_parents(self)
        for cluster in self.clusters:
            cluster.resolve_parents(self)

    def iter_mems(self) -> Iterable[Memory]:
        yield self.memory
        for cluster in self.clusters:
            yield cluster.memory

    def find_mem(self, attr: StringAttr) -> Memory:
        for memory in self.iter_mems():
            if memory.attribute == attr:
                return memory
        raise RuntimeError(f"Could not find memory {str(attr)}")

    def iter_accelerators(self) -> Iterable[Accelerator]:
        for cluster in self.clusters:
            for core in cluster.cores:
                yield from core.accelerators

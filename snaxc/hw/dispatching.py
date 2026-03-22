from abc import ABC
from collections.abc import Iterable
from dataclasses import dataclass

from xdsl.ir import Attribute, Operation

from snaxc.dialects.kernel import KernelOp
from snaxc.hw.system import Accelerator


@dataclass
class SupportedKernel:
    kernel_type: type[KernelOp]
    operand_types: Iterable[Attribute]

    def is_same_kernel(self, kernel_op: Operation | None) -> bool:
        """
        Check if the kernel operation matches the supported kernel type and operand types.
        """
        if not isinstance(kernel_op, self.kernel_type):
            return False
        return list(self.operand_types) == [*kernel_op.operand_types, *kernel_op.result_types]


@dataclass
class DispatchTemplate(Accelerator, ABC):
    """
    Specifies a dispatching template to dispatch linalg generic kernels to accelerators.
    """

    supported_kernels: Iterable[SupportedKernel]

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import (
    IndexType,
    IntegerAttr,
    IntegerType,
    MemRefLayoutAttr,
    MemRefType,
    NoneAttr,
    UnrankedMemRefType,
    i32,
)
from xdsl.dialects.llvm import LLVMStructType
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import (
    IRDLOperation,
    Operand,
    OpResult,
    VarOperand,
    irdl_op_definition,
    operand_def,
    opt_prop_def,
    result_def,
    traits_def,
    var_operand_def,
)
from xdsl.traits import Pure
from xdsl.utils.exceptions import VerifyException

from snaxc.util.memref_descriptor import LLVMMemrefDescriptor


@irdl_op_definition
class ClusterSyncOp(IRDLOperation):
    """Cluster sync operation for a snax cluster. This
    translates directly to the C function snrt_cluster_hw_barrier()"""

    name = "snax.cluster_sync_op"


@irdl_op_definition
class HartIdOp(IRDLOperation):
    """Retrieve the hart id of the current core"""

    name = "snax.hart_id"

    result = result_def(IndexType)

    traits = traits_def(Pure())

    def __init__(self):
        return super().__init__(result_types=[IndexType()])


@irdl_op_definition
class MCycleOp(IRDLOperation):
    """Utility operation that translates to risc-v mcycle instruction
    for trace annotation."""

    name = "snax.mcycle"


@irdl_op_definition
class LayoutCast(IRDLOperation):
    """LayoutCast operation for memrefs in a snax cluster. This
    operation is used to change the layout of the memref data"""

    name = "snax.layout_cast"

    source = operand_def(MemRefType)
    dest = result_def(MemRefType)

    def __init__(
        self,
        source: SSAValue | Operation,
        dest: MemRefType[Attribute] | UnrankedMemRefType[Attribute],
    ):
        super().__init__(operands=[source], result_types=[dest])

    @staticmethod
    def from_type_and_target_layout(
        source: SSAValue | Operation,
        layout: MemRefLayoutAttr,
    ) -> LayoutCast:
        source = SSAValue.get(source)
        assert isinstance(source.type, Attribute)
        source_type = cast(MemRefType[Attribute], source.type)
        dest = MemRefType(
            source_type.get_element_type(),
            source_type.get_shape(),
            layout=layout,
            memory_space=source_type.memory_space,
        )
        return LayoutCast(source, dest)

    def verify_(self) -> None:
        source = cast(MemRefType[Attribute], self.source.type)
        dest = self.dest.type
        if source.get_shape() != dest.get_shape():
            raise VerifyException("Expected source and destination to have the same shape.")
        if source.get_element_type() != dest.get_element_type():
            raise VerifyException("Expected source and destination to have the same element type.")
        if source.memory_space != dest.memory_space:
            raise VerifyException("Expected source and destination to have the same memory space.")


@irdl_op_definition
class Alloc(IRDLOperation):
    """Alloc operation in a snax cluster.

    Contrary to a memref.alloc, this operation does not generate
    a memref. Instead, it returns an llvm struct memref descriptor.
    When other operations get lowered to llvm, the llvm structs will
    match and the conversion casts can be realized.
    """

    name = "snax.alloc"

    size: Operand = operand_def(IndexType)
    shapes: VarOperand = var_operand_def(IndexType)
    result: OpResult = result_def(LLVMStructType)
    memory_space: Attribute | None = opt_prop_def(Attribute)
    alignment: IntegerAttr | None = opt_prop_def(IntegerAttr)

    def __init__(
        self,
        rank: int,
        size: SSAValue | Operation,
        shapes: Sequence[SSAValue | Operation],
        memory_space: Attribute = NoneAttr(),
        alignment: IntegerAttr | None = None,
        integer_type: IntegerType = i32,
    ):
        # output type is llvm struct memref descriptor
        descriptor = LLVMMemrefDescriptor.from_rank_and_integer_type(rank, integer_type)

        if not alignment:
            alignment = IntegerAttr(1, IntegerType(64))

        super().__init__(
            operands=[size, shapes],
            result_types=[descriptor.descriptor],
            properties={"memory_space": memory_space, "alignment": alignment},
        )

    def verify_(self) -> None:
        # check for a correct result type
        if not isinstance(self.result.type, LLVMStructType):
            raise VerifyException("Expected result type to be LLVMStructType")

        descriptor = LLVMMemrefDescriptor(self.result.type)
        descriptor.verify()


@irdl_op_definition
class ClearL1(IRDLOperation):
    """
    Claer L1 memory, setting everything to zero.
    Every allocated memref in L1 is now invalidated.
    """

    name = "snax.clear_l1"


Snax = Dialect(
    "snax",
    [ClusterSyncOp, MCycleOp, LayoutCast, Alloc, ClearL1, HartIdOp],
    [],
)

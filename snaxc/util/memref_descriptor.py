from xdsl.dialects.builtin import IntegerType, MemRefType, Signedness
from xdsl.dialects.llvm import LLVMArrayType, LLVMPointerType, LLVMStructType
from xdsl.ir import Attribute
from xdsl.utils.exceptions import VerifyException
from xdsl.utils.hints import isa

# this file contains useful helper functions to work with
# llvm struct memref descriptors, which are used for lowering
# memrefs to llvm ir. The memref descriptor is a struct that
# contains all the necessary information to access a memref
# in memory.

# See https://mlir.llvm.org/docs/TargetLLVMIR/#default-calling-convention-for-ranked-memref
# for more information on the layout of the memref descriptor.


class LLVMMemrefDescriptor:
    """A class to work with LLVM memref descriptors.
    https://mlir.llvm.org/docs/TargetLLVMIR/#default-calling-convention-for-ranked-memref
    """

    descriptor: LLVMStructType

    def __init__(self, descriptor: LLVMStructType):
        """
        Initializes a new instance of the MemrefDescriptor class.

        Args:
            descriptor (LLVMStructType): The descriptor for the memref.
        """
        self.descriptor = descriptor

    @classmethod
    def from_rank_and_integer_type(cls, rank: int, integer_type: IntegerType) -> "LLVMMemrefDescriptor":
        """
        Create an LLVMMemrefDescriptor from a dimension and an integer type.

        Args:
            rank (int): The rank of the memref.
            integer_type (IntegerType): The integer type of the memref.

        Returns:
            LLVMMemrefDescriptor: The created descriptor.
        """

        # MLIR's default calling convention for ranked memrefs (matched by
        # `--finalize-memref-to-llvm`) drops the sizes/strides arrays when
        # rank is 0 — only the allocated/aligned pointers and offset remain.
        # Keeping those arrays here as `LLVMArrayType(0, ...)` would diverge
        # from the mlir-opt convention and leave an unreconcilable
        # `builtin.unrealized_conversion_cast` between the snax-side 5-field
        # struct and the mlir-side 3-field struct.
        fields: list[Attribute] = [
            LLVMPointerType(),
            LLVMPointerType(),
            integer_type,
        ]
        if rank > 0:
            fields.extend(
                [
                    LLVMArrayType(rank, integer_type),
                    LLVMArrayType(rank, integer_type),
                ]
            )

        return cls(LLVMStructType.from_type_list(fields))

    @classmethod
    def from_memref_type(cls, memref_type: MemRefType[Attribute], integer_type: IntegerType) -> "LLVMMemrefDescriptor":
        """
        Create an LLVMMemrefDescriptor from a MemRefType.

        Args:
            memref_type (MemRefType): The MemRefType to create the descriptor from.
            integer_type (IntegerType): The integer type for the memref descriptor.

        Returns:
            LLVMMemrefDescriptor: The created descriptor.
        """

        el_type = memref_type.get_element_type()
        assert isa(el_type, IntegerType[int, Signedness])

        return cls.from_rank_and_integer_type(memref_type.get_num_dims(), el_type)

    def verify(self) -> None:
        """
        Verify the validity of a memref descriptor.

        Raises:
            VerifyException: If the memref descriptor is invalid.
        """

        def exception(message: str) -> VerifyException:
            return VerifyException("Invalid Memref Descriptor: " + message)

        types = self.descriptor.types.data

        if len(types) not in (3, 5):
            raise exception("Expected descriptor to have 3 (0-D) or 5 (ranked) fields")

        if not isinstance(types[0], LLVMPointerType):
            raise exception("Expected first element to be LLVMPointerType")

        if not isinstance(types[1], LLVMPointerType):
            raise exception("Expected second element to be LLVMPointerType")

        if not isinstance(types[2], IntegerType):
            raise exception("Expected third element to be IntegerType")

        if len(types) == 3:
            # 0-D memref descriptor: pointer + aligned_pointer + offset only.
            return

        shape = types[3]
        if not isinstance(shape, LLVMArrayType):
            raise exception("Expected fourth element to be LLVMArrayType")

        if not isinstance(shape.type, IntegerType):
            raise exception("Expected fourth element to be LLVMArrayType of IntegerType")

        strides = types[4]
        if not isinstance(strides, LLVMArrayType):
            raise exception("Expected fifth element to be LLVMArrayType")

        if not isinstance(strides.type, IntegerType):
            raise exception("Expected fifth element to be LLVMArrayType of IntegerType")

        if not strides.size.data == shape.size.data:
            raise exception("Expected shape and strides to have the same dimension")

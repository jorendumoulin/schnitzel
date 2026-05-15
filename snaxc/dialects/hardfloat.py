from __future__ import annotations

from abc import ABC
from collections.abc import Sequence
from typing import ClassVar, cast

from xdsl.dialects.builtin import IntAttr, IntegerType
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, irdl_op_definition, operand_def, opt_prop_def, prop_def, result_def, traits_def
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.traits import Pure
from xdsl.utils.exceptions import VerifyException
from xdsl.utils.hints import isa


class HardfloatOperation(IRDLOperation, ABC):
    sig_width = prop_def(IntAttr)
    exp_width = prop_def(IntAttr)
    int_width = opt_prop_def(IntAttr)

    traits = traits_def(Pure())

    def __init__(
        self,
        operands: Sequence[Operation | SSAValue],
        result_types: Sequence[Attribute],
        sig_width: int,
        exp_width: int,
        int_width: int | None = None,
        attr_dict: dict[str, Attribute] | None = None,
        prop_dict: dict[str, Attribute] | None = None,
    ):
        props: dict[str, Attribute] = {}
        props.update({"exp_width": IntAttr(exp_width), "sig_width": IntAttr(sig_width)})
        if int_width is not None:
            props["int_width"] = IntAttr(int_width)
        if prop_dict is not None:
            props.update(prop_dict)
        super().__init__(operands=operands, result_types=result_types, attributes=attr_dict, properties=props)

    def print(self, printer: Printer):
        if self.int_width is not None:
            printer.print_string(f"<{self.sig_width.data}, {self.exp_width.data}, {self.int_width.data}>")
        else:
            printer.print_string(f"<{self.sig_width.data}, {self.exp_width.data}>")
        printer.print_operands(self.operands)
        opt_properties = {
            name: attr for name, attr in self.properties.items() if name not in ["sig_width", "exp_width", "int_width"]
        }
        if len(opt_properties) > 0:
            printer.print_string(" ")
            with printer.in_angle_brackets():
                printer.print_attr_dict(opt_properties)
        printer.print_string(" : ")
        printer.print_function_type(input_types=self.operand_types, output_types=self.result_types)

    @classmethod
    def parse(cls, parser: Parser) -> HardfloatOperation:
        parser.parse_punctuation("<")
        sig_width = parser.parse_integer(allow_boolean=False, allow_negative=False)
        parser.parse_punctuation(",")
        exp_width = parser.parse_integer(allow_boolean=False, allow_negative=False)
        parser.parse_optional_punctuation(",")
        int_width = parser.parse_optional_integer(allow_boolean=False, allow_negative=False)
        parser.parse_punctuation(">")
        operands = parser.parse_comma_separated_list(
            delimiter=parser.Delimiter.PAREN, parse=parser.parse_unresolved_operand
        )
        prop_dict = parser.parse_optional_properties_dict()
        parser.parse_punctuation(":")
        func_type = parser.parse_function_type()
        in_types = func_type.inputs.data
        out_types = func_type.outputs.data
        res_operands: list[SSAValue[Attribute]] = []
        for opnd, typ in zip(operands, in_types, strict=True):
            res_operands.append(parser.resolve_operand(opnd, typ))
        return cls(
            operands=res_operands,
            result_types=out_types,
            sig_width=sig_width,
            exp_width=exp_width,
            int_width=int_width,
            prop_dict=prop_dict,
        )

    def get_chisel_name(self) -> str:
        chisel_name = getattr(self, "CHISEL_NAME")
        assert isinstance(chisel_name, str), f"{self.__class__.__name__} needs to set a CHISEL_NAME ClassVar"
        return chisel_name

    def get_suffix(self) -> str:
        if self.int_width is None:
            return f"_s{self.sig_width.data}_e{self.exp_width.data}"
        return f"_i{self.int_width.data}_s{self.sig_width.data}_e{self.exp_width.data}"

    def get_chisel_input_names(self) -> Sequence[str]:
        chisel_input_names = getattr(self, "CHISEL_INPUT_NAMES")
        assert isa(chisel_input_names, Sequence[str]), (
            f"{self.__class__.__name__} needs to set a CHISEL_INPUT_NAMES ClassVar"
        )
        return chisel_input_names

    def get_chisel_output_names(self) -> Sequence[str]:
        chisel_output_names = getattr(self, "CHISEL_OUTPUT_NAMES")
        assert isa(chisel_output_names, Sequence[str]), (
            f"{self.__class__.__name__} needs to set a CHISEL_OUTPUT_NAMES ClassVar"
        )
        return chisel_output_names


def verify_recoded(op: HardfloatOperation, typ: Attribute) -> None:
    sig_width, exp_width = (op.sig_width.data, op.exp_width.data)
    bit_width = cast(IntegerType, typ).bitwidth
    if bit_width != sig_width + exp_width + 1:
        raise VerifyException(
            f"Expect type ({typ}) to be equal to sig_width ({sig_width}) + exp_width ({exp_width}) + 1"
        )


def verify_float(op: HardfloatOperation, typ: Attribute) -> None:
    sig_width, exp_width = (op.sig_width.data, op.exp_width.data)
    bit_width = cast(IntegerType, typ).bitwidth
    if bit_width != sig_width + exp_width:
        raise VerifyException(f"Expect type ({typ}) to be equal to sig_width ({sig_width}) + exp_width ({exp_width})")


def verify_int(op: HardfloatOperation, typ: Attribute):
    if op.int_width is None:
        raise VerifyException("Expect op to have int_width property")
    if cast(IntegerType, typ).bitwidth != op.int_width.data:
        raise VerifyException(f"Expect type ({typ}) to have bitwidth given by int_width property ({op.int_width.data})")


@irdl_op_definition
class MulRecFnOp(HardfloatOperation):
    CHISEL_NAME: ClassVar[str] = "MulRecFN"
    CHISEL_INPUT_NAMES: ClassVar[tuple[str, ...]] = ("a", "b", "roundingMode", "detectTininess")
    CHISEL_OUTPUT_NAMES: ClassVar[tuple[str, ...]] = ("out", "exceptionFlags")
    name = "hardfloat.mul_rec_fn"
    a = operand_def(IntegerType)
    b = operand_def(IntegerType)
    roundingMode = operand_def(IntegerType(3))
    detectTininess = operand_def(IntegerType(1))
    out = result_def(IntegerType)
    exceptionFlags = result_def(IntegerType(5))

    def verify_(self) -> None:
        verify_recoded(self, self.a.type)
        verify_recoded(self, self.b.type)
        verify_recoded(self, self.out.type)


@irdl_op_definition
class AddRecFnOp(HardfloatOperation):
    CHISEL_NAME: ClassVar[str] = "AddRecFN"
    CHISEL_INPUT_NAMES: ClassVar[tuple[str, ...]] = ("subOp", "a", "b", "roundingMode", "detectTininess")
    CHISEL_OUTPUT_NAMES: ClassVar[tuple[str, ...]] = ("out", "exceptionFlags")
    name = "hardfloat.add_rec_fn"
    subOp = operand_def(IntegerType(1))
    a = operand_def(IntegerType)
    b = operand_def(IntegerType)
    roundingMode = operand_def(IntegerType(3))
    detectTininess = operand_def(IntegerType(1))
    out = result_def(IntegerType)
    exceptionFlags = result_def(IntegerType(5))

    def verify_(self) -> None:
        verify_recoded(self, self.a.type)
        verify_recoded(self, self.b.type)
        verify_recoded(self, self.out.type)


@irdl_op_definition
class FnToRecFnOp(HardfloatOperation):
    CHISEL_NAME: ClassVar[str] = "recFNFromFN"
    CHISEL_INPUT_NAMES: ClassVar[tuple[str, ...]] = ("in",)
    CHISEL_OUTPUT_NAMES: ClassVar[tuple[str, ...]] = ("out",)
    name = "hardfloat.fn_to_rec_fn"
    in_ = operand_def(IntegerType)  # "in" is reserved in python
    out = result_def(IntegerType)

    def verify_(self) -> None:
        verify_float(self, self.in_.type)
        verify_recoded(self, self.out.type)


@irdl_op_definition
class RecFnToFnOp(HardfloatOperation):
    CHISEL_NAME: ClassVar[str] = "fNFromRecFN"
    CHISEL_INPUT_NAMES: ClassVar[tuple[str, ...]] = ("in",)
    CHISEL_OUTPUT_NAMES: ClassVar[tuple[str, ...]] = ("out",)
    name = "hardfloat.rec_fn_to_fn"
    in_ = operand_def(IntegerType)  # "in" is reserved in python
    out = result_def(IntegerType)

    def verify_(self) -> None:
        verify_recoded(self, self.in_.type)
        verify_float(self, self.out.type)


@irdl_op_definition
class InToRecFnOp(HardfloatOperation):
    CHISEL_NAME: ClassVar[str] = "INToRecFN"
    CHISEL_INPUT_NAMES: ClassVar[tuple[str, ...]] = ("signedIn", "in", "roundingMode", "detectTininess")
    CHISEL_OUTPUT_NAMES: ClassVar[tuple[str, ...]] = ("out", "exceptionFlags")
    name = "hardfloat.in_to_rec_fn"
    signedIn = operand_def(IntegerType(1))
    in_ = operand_def(IntegerType)  # "in" is reserved in python
    roundingMode = operand_def(IntegerType(3))
    detectTininess = operand_def(IntegerType(1))
    out = result_def(IntegerType)
    exceptionFlags = result_def(IntegerType(5))

    def verify_(self) -> None:
        verify_int(self, self.in_.type)
        verify_recoded(self, self.out.type)


@irdl_op_definition
class MulAddRecFnOp(HardfloatOperation):
    """
    Fused multiply-add on recoded floats. `op` is a 2-bit field selecting
    a*b+c (0), a*b-c (1), -(a*b)+c (2), -(a*b)-c (3).
    """

    CHISEL_NAME: ClassVar[str] = "MulAddRecFN"
    CHISEL_INPUT_NAMES: ClassVar[tuple[str, ...]] = ("op", "a", "b", "c", "roundingMode", "detectTininess")
    CHISEL_OUTPUT_NAMES: ClassVar[tuple[str, ...]] = ("out", "exceptionFlags")
    name = "hardfloat.mul_add_rec_fn"
    op = operand_def(IntegerType(2))
    a = operand_def(IntegerType)
    b = operand_def(IntegerType)
    c = operand_def(IntegerType)
    roundingMode = operand_def(IntegerType(3))
    detectTininess = operand_def(IntegerType(1))
    out = result_def(IntegerType)
    exceptionFlags = result_def(IntegerType(5))

    def verify_(self) -> None:
        verify_recoded(self, self.a.type)
        verify_recoded(self, self.b.type)
        verify_recoded(self, self.c.type)
        verify_recoded(self, self.out.type)


@irdl_op_definition
class RecFnToRecFnOp(HardfloatOperation):
    """
    Convert one recoded float format to another (trunc/ext).

    The base sig_width/exp_width describe the INPUT format; out_sig_width/
    out_exp_width describe the OUTPUT format. Surface syntax is
    `<in_sig, in_exp, out_sig, out_exp>`.
    """

    CHISEL_NAME: ClassVar[str] = "RecFNToRecFN"
    CHISEL_INPUT_NAMES: ClassVar[tuple[str, ...]] = ("in", "roundingMode", "detectTininess")
    CHISEL_OUTPUT_NAMES: ClassVar[tuple[str, ...]] = ("out", "exceptionFlags")
    name = "hardfloat.rec_fn_to_rec_fn"
    out_sig_width = prop_def(IntAttr)
    out_exp_width = prop_def(IntAttr)
    in_ = operand_def(IntegerType)
    roundingMode = operand_def(IntegerType(3))
    detectTininess = operand_def(IntegerType(1))
    out = result_def(IntegerType)
    exceptionFlags = result_def(IntegerType(5))

    def __init__(
        self,
        operands: Sequence[Operation | SSAValue],
        result_types: Sequence[Attribute],
        in_sig_width: int,
        in_exp_width: int,
        out_sig_width: int,
        out_exp_width: int,
        attr_dict: dict[str, Attribute] | None = None,
        prop_dict: dict[str, Attribute] | None = None,
    ):
        props: dict[str, Attribute] = {
            "out_sig_width": IntAttr(out_sig_width),
            "out_exp_width": IntAttr(out_exp_width),
        }
        if prop_dict is not None:
            props.update(prop_dict)
        super().__init__(
            operands=operands,
            result_types=result_types,
            sig_width=in_sig_width,
            exp_width=in_exp_width,
            attr_dict=attr_dict,
            prop_dict=props,
        )

    def verify_(self) -> None:
        verify_recoded(self, self.in_.type)
        out_bw = self.out.type.bitwidth
        if out_bw != self.out_sig_width.data + self.out_exp_width.data + 1:
            raise VerifyException(
                f"Expect output type ({self.out.type}) to be equal to out_sig_width ({self.out_sig_width.data}) "
                f"+ out_exp_width ({self.out_exp_width.data}) + 1"
            )

    def print(self, printer: Printer):
        printer.print_string(
            f"<{self.sig_width.data}, {self.exp_width.data}, {self.out_sig_width.data}, {self.out_exp_width.data}>"
        )
        printer.print_operands(self.operands)
        printer.print_string(" : ")
        printer.print_function_type(input_types=self.operand_types, output_types=self.result_types)

    @classmethod
    def parse(cls, parser: Parser) -> RecFnToRecFnOp:
        parser.parse_punctuation("<")
        in_sig = parser.parse_integer(allow_boolean=False, allow_negative=False)
        parser.parse_punctuation(",")
        in_exp = parser.parse_integer(allow_boolean=False, allow_negative=False)
        parser.parse_punctuation(",")
        out_sig = parser.parse_integer(allow_boolean=False, allow_negative=False)
        parser.parse_punctuation(",")
        out_exp = parser.parse_integer(allow_boolean=False, allow_negative=False)
        parser.parse_punctuation(">")
        operands = parser.parse_comma_separated_list(
            delimiter=parser.Delimiter.PAREN, parse=parser.parse_unresolved_operand
        )
        parser.parse_punctuation(":")
        func_type = parser.parse_function_type()
        in_types = func_type.inputs.data
        out_types = func_type.outputs.data
        res_operands: list[SSAValue[Attribute]] = []
        for opnd, typ in zip(operands, in_types, strict=True):
            res_operands.append(parser.resolve_operand(opnd, typ))
        return cls(
            operands=res_operands,
            result_types=out_types,
            in_sig_width=in_sig,
            in_exp_width=in_exp,
            out_sig_width=out_sig,
            out_exp_width=out_exp,
        )

    def get_suffix(self) -> str:
        return (
            f"_is{self.sig_width.data}_ie{self.exp_width.data}_os{self.out_sig_width.data}_oe{self.out_exp_width.data}"
        )


@irdl_op_definition
class CompareRecFnOp(HardfloatOperation):
    CHISEL_NAME: ClassVar[str] = "CompareRecFN"
    CHISEL_INPUT_NAMES: ClassVar[tuple[str, ...]] = ("a", "b", "signaling")
    CHISEL_OUTPUT_NAMES: ClassVar[tuple[str, ...]] = ("lt", "eq", "gt", "exceptionFlags")
    name = "hardfloat.compare_rec_fn"
    a = operand_def(IntegerType)
    b = operand_def(IntegerType)
    signaling = operand_def(IntegerType(1))
    lt = result_def(IntegerType(1))
    eq = result_def(IntegerType(1))
    gt = result_def(IntegerType(1))
    exceptionFlags = result_def(IntegerType(5))

    def verify_(self) -> None:
        verify_recoded(self, self.a.type)
        verify_recoded(self, self.b.type)


@irdl_op_definition
class RecFnToInOp(HardfloatOperation):
    CHISEL_NAME: ClassVar[str] = "RecFNToIN"
    CHISEL_INPUT_NAMES: ClassVar[tuple[str, ...]] = ("in", "roundingMode", "signedOut")
    CHISEL_OUTPUT_NAMES: ClassVar[tuple[str, ...]] = ("out", "exceptionFlags")
    name = "hardfloat.rec_fn_to_in"
    in_ = operand_def(IntegerType)  # "in" is reserved in python
    roundingMode = operand_def(IntegerType(3))
    signedOut = operand_def(IntegerType(1))
    out = result_def(IntegerType)
    # conversions to integer can never underflow or deliver an infinite result
    exceptionFlags = result_def(IntegerType(3))  # So this is 3 bits instead of 5

    def verify_(self) -> None:
        verify_recoded(self, self.in_.type)
        verify_int(self, self.out.type)


Hardfloat = Dialect(
    "hardfloat",
    [
        MulRecFnOp,
        AddRecFnOp,
        RecFnToFnOp,
        FnToRecFnOp,
        InToRecFnOp,
        RecFnToInOp,
        CompareRecFnOp,
        RecFnToRecFnOp,
        MulAddRecFnOp,
    ],
)

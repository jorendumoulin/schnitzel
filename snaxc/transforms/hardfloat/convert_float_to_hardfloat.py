from __future__ import annotations

from typing import cast

from xdsl.context import Context
from xdsl.dialects import arith, hw, math
from xdsl.dialects.builtin import (
    AnyFloat,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntegerType,
    ModuleOp,
    UnrealizedConversionCastOp,
)
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from snaxc.dialects.hardfloat import (
    AddRecFnOp,
    CompareRecFnOp,
    FnToRecFnOp,
    InToRecFnOp,
    MulAddRecFnOp,
    MulRecFnOp,
    RecFnToFnOp,
    RecFnToInOp,
    RecFnToRecFnOp,
)

_type_mapping: dict[type[Attribute], tuple[int, int]] = {
    Float64Type: (11, 53),
    Float32Type: (8, 24),
    Float16Type: (5, 11),
    BFloat16Type: (8, 8),
}


class ConvertAddSubOp(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.AddfOp | arith.SubfOp, rewriter: PatternRewriter):
        # Get sig_width and exp_witdh:
        in_type = cast(AnyFloat, op.lhs.type)  # These are verified by IRDL
        if type(in_type) not in _type_mapping:
            return
        exp_width, sig_width = _type_mapping[type(in_type)]
        bitwidth = in_type.bitwidth
        match op:
            case arith.AddfOp():
                subOp = hw.ConstantOp(0, 1)
            case arith.SubfOp():
                subOp = hw.ConstantOp(1, 1)
        # Create the recode - core_op - unrecode sandwich
        new_ops = [
            subOp,
            cast_lhs := UnrealizedConversionCastOp.get([op.lhs], [IntegerType(bitwidth)]),
            cast_rhs := UnrealizedConversionCastOp.get([op.rhs], [IntegerType(bitwidth)]),
            recode_lhs := FnToRecFnOp([cast_lhs], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            recode_rhs := FnToRecFnOp([cast_rhs], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            rounding_mode := hw.ConstantOp(0, 3),
            tininess := hw.ConstantOp(1, 1),
            add := AddRecFnOp(
                [subOp, recode_lhs, recode_rhs, rounding_mode, tininess],
                [IntegerType(bitwidth + 1), IntegerType(5)],
                sig_width,
                exp_width,
            ),
            unrecode := RecFnToFnOp([add.results[0]], [IntegerType(bitwidth)], sig_width, exp_width),
            cast_res := UnrealizedConversionCastOp.get([unrecode], [in_type]),
        ]
        rewriter.replace_op(op, new_ops=new_ops, new_results=[cast_res.results[0]])


class ConvertMulOp(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.MulfOp, rewriter: PatternRewriter):
        # Get sig_width and exp_witdh:
        in_type = cast(AnyFloat, op.lhs.type)  # These are verified by IRDL
        if type(in_type) not in _type_mapping:
            return
        exp_width, sig_width = _type_mapping[type(in_type)]
        bitwidth = in_type.bitwidth

        # Create the recode - core_op - unrecode sandwich
        new_ops = [
            cast_lhs := UnrealizedConversionCastOp.get([op.lhs], [IntegerType(bitwidth)]),
            cast_rhs := UnrealizedConversionCastOp.get([op.rhs], [IntegerType(bitwidth)]),
            recode_lhs := FnToRecFnOp([cast_lhs], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            recode_rhs := FnToRecFnOp([cast_rhs], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            rounding_mode := hw.ConstantOp(0, 3),
            tininess := hw.ConstantOp(1, 1),
            mul := MulRecFnOp(
                [recode_lhs, recode_rhs, rounding_mode, tininess],
                [IntegerType(bitwidth + 1), IntegerType(5)],
                sig_width,
                exp_width,
            ),
            unrecode := RecFnToFnOp([mul.results[0]], [IntegerType(bitwidth)], sig_width, exp_width),
            cast_res := UnrealizedConversionCastOp.get([unrecode], [in_type]),
        ]
        rewriter.replace_op(op, new_ops=new_ops, new_results=[cast_res.results[0]])


class ConvertIToFPOp(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.SIToFPOp | arith.UIToFPOp, rewriter: PatternRewriter):
        match op:
            case arith.SIToFPOp():
                signed_in = hw.ConstantOp(1, 1)
            case arith.UIToFPOp():
                signed_in = hw.ConstantOp(0, 1)
        exp_width, sig_width = _type_mapping[type(op.result.type)]
        bitwidth = cast(IntegerType, op.input.type).bitwidth
        new_ops = [
            signed_in,
            rounding_mode := hw.ConstantOp(0, 3),
            tininess := hw.ConstantOp(1, 1),
            conversion := InToRecFnOp(
                [signed_in.result, op.input, rounding_mode, tininess],
                [IntegerType(bitwidth + 1), IntegerType(5)],
                sig_width,
                exp_width,
                bitwidth,
            ),
            unrecode := RecFnToFnOp([conversion.results[0]], [IntegerType(bitwidth)], sig_width, exp_width),
            cast_res := UnrealizedConversionCastOp.get([unrecode], [op.result.type]),
        ]
        rewriter.replace_op(op, new_ops=new_ops, new_results=[cast_res.results[0]])


class ConvertFPToIOp(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.FloatingPointToIntegerBaseOp, rewriter: PatternRewriter):
        match op.name:
            case arith.FPToSIOp.name:
                signed_out = hw.ConstantOp(1, 1)
            case arith.FPToUIOp.name:
                signed_out = hw.ConstantOp(0, 1)
            case _:
                raise NotImplementedError()
        exp_width, sig_width = _type_mapping[type(op.input.type)]
        bitwidth = cast(IntegerType, op.input.type).bitwidth
        new_ops = [
            signed_out,
            rounding_mode := hw.ConstantOp(0, 3),
            cast_res := UnrealizedConversionCastOp.get([op.input], [op.result.type]),
            recode := FnToRecFnOp([cast_res], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            rec_fn := RecFnToInOp(
                [recode, rounding_mode, signed_out],
                [IntegerType(bitwidth), IntegerType(3)],
                sig_width,
                exp_width,
                bitwidth,
            ),
        ]
        rewriter.replace_op(op, new_ops=new_ops, new_results=[rec_fn.results[0]])


class ConvertFmaOp(RewritePattern):
    """Lower math.fma(a, b, c) = a*b+c via hardfloat.mul_add_rec_fn (op=0)."""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: math.FmaOp, rewriter: PatternRewriter):
        in_type = cast(AnyFloat, op.a.type)
        if type(in_type) not in _type_mapping:
            return
        exp_width, sig_width = _type_mapping[type(in_type)]
        bitwidth = in_type.bitwidth

        new_ops: list[Operation] = [
            cast_a := UnrealizedConversionCastOp.get([op.a], [IntegerType(bitwidth)]),
            cast_b := UnrealizedConversionCastOp.get([op.b], [IntegerType(bitwidth)]),
            cast_c := UnrealizedConversionCastOp.get([op.c], [IntegerType(bitwidth)]),
            recode_a := FnToRecFnOp([cast_a], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            recode_b := FnToRecFnOp([cast_b], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            recode_c := FnToRecFnOp([cast_c], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            fma_op := hw.ConstantOp(0, 2),
            rm := hw.ConstantOp(0, 3),
            tininess := hw.ConstantOp(1, 1),
            fma := MulAddRecFnOp(
                [fma_op, recode_a, recode_b, recode_c, rm, tininess],
                [IntegerType(bitwidth + 1), IntegerType(5)],
                sig_width,
                exp_width,
            ),
            unrecode := RecFnToFnOp([fma.results[0]], [IntegerType(bitwidth)], sig_width, exp_width),
            cast_res := UnrealizedConversionCastOp.get([unrecode], [in_type]),
        ]
        rewriter.replace_op(op, new_ops=new_ops, new_results=[cast_res.results[0]])


class ConvertTruncExtfOp(RewritePattern):
    """
    Lower arith.truncf / arith.extf via hardfloat.rec_fn_to_rec_fn.

    Sandwich: cast input float→int, recode to input recoded format, dispatch
    through rec_fn_to_rec_fn to the output recoded format, decode, cast back.
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.ExtFOp | arith.TruncFOp, rewriter: PatternRewriter):
        in_type = cast(AnyFloat, op.input.type)
        out_type = op.result.type
        if type(in_type) not in _type_mapping or type(out_type) not in _type_mapping:
            return
        in_exp, in_sig = _type_mapping[type(in_type)]
        out_exp, out_sig = _type_mapping[type(out_type)]
        in_bw = in_type.bitwidth
        out_bw = out_type.bitwidth

        new_ops: list[Operation] = [
            cast_in := UnrealizedConversionCastOp.get([op.input], [IntegerType(in_bw)]),
            recode := FnToRecFnOp([cast_in], [IntegerType(in_bw + 1)], in_sig, in_exp),
            rm := hw.ConstantOp(0, 3),
            tininess := hw.ConstantOp(1, 1),
            convert := RecFnToRecFnOp(
                [recode, rm, tininess],
                [IntegerType(out_bw + 1), IntegerType(5)],
                in_sig,
                in_exp,
                out_sig,
                out_exp,
            ),
            decode := RecFnToFnOp([convert.results[0]], [IntegerType(out_bw)], out_sig, out_exp),
            cast_out := UnrealizedConversionCastOp.get([decode], [out_type]),
        ]
        rewriter.replace_op(op, new_ops=new_ops, new_results=[cast_out.results[0]])


class ConvertMaximumMinimumOp(RewritePattern):
    """
    Lower arith.maximumf / arith.minimumf with IEEE-754-2019 semantics:
      * If either operand is NaN, the result is qNaN.
      * -0.0 is treated as strictly less than +0.0 (so maximumf(+0,-0) = +0,
        minimumf(+0,-0) = -0).

    CompareRecFN reports eq=1 for any (±0, ±0) pair regardless of sign, so the
    sign-aware tie-break is handled here. The MSB of the IEEE-encoded operand
    is the sign bit, so we use `arith.cmpi slt %op_i, 0` to test it.

    Logic:
      ord  = lt | eq | gt    (false iff at least one operand is NaN)
      For max: pick_lhs = gt | (eq & !lhs_neg)
      For min: pick_lhs = lt | (eq &  lhs_neg)
      pick = pick_lhs ? lhs : rhs
      out  = ord ? pick : qNaN
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.MaximumfOp | arith.MinimumfOp, rewriter: PatternRewriter):
        in_type = cast(AnyFloat, op.lhs.type)
        if type(in_type) not in _type_mapping:
            return
        exp_width, sig_width = _type_mapping[type(in_type)]
        bitwidth = in_type.bitwidth
        is_max = isinstance(op, arith.MaximumfOp)

        # qNaN bit pattern: sign=0, exp all 1s, mantissa MSB set.
        exp_bits = (1 << exp_width) - 1
        nan_int = (exp_bits << (sig_width - 1)) | (1 << (sig_width - 2))

        new_ops: list[Operation] = [
            cast_lhs := UnrealizedConversionCastOp.get([op.lhs], [IntegerType(bitwidth)]),
            cast_rhs := UnrealizedConversionCastOp.get([op.rhs], [IntegerType(bitwidth)]),
            recode_lhs := FnToRecFnOp([cast_lhs], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            recode_rhs := FnToRecFnOp([cast_rhs], [IntegerType(bitwidth + 1)], sig_width, exp_width),
            signaling := hw.ConstantOp(0, 1),
            cmp := CompareRecFnOp(
                [recode_lhs, recode_rhs, signaling],
                [IntegerType(1), IntegerType(1), IntegerType(1), IntegerType(5)],
                sig_width,
                exp_width,
            ),
            zero_int := hw.ConstantOp(0, bitwidth),
            lhs_neg := arith.CmpiOp(cast_lhs, zero_int, "slt"),
        ]
        lt, eq, gt, _flags = cmp.results

        # Tie-break selector: for max we want lhs_nonneg = !lhs_neg.
        if is_max:
            one_i1 = hw.ConstantOp(1, 1)
            lhs_nonneg = arith.XOrIOp(lhs_neg, one_i1)
            new_ops.extend([one_i1, lhs_nonneg])
            tie_cond = lhs_nonneg.result
        else:
            tie_cond = lhs_neg.result

        eq_and_tie = arith.AndIOp(eq, tie_cond)
        primary = gt if is_max else lt
        pick_lhs = arith.OrIOp(primary, eq_and_tie)
        ord_lt_eq = arith.OrIOp(lt, eq)
        ord_val = arith.OrIOp(ord_lt_eq, gt)
        pick = arith.SelectOp(pick_lhs, op.lhs, op.rhs)
        nan_const_int = hw.ConstantOp(nan_int, bitwidth)
        nan_const_float = UnrealizedConversionCastOp.get([nan_const_int], [in_type])
        result = arith.SelectOp(ord_val, pick, nan_const_float.results[0])

        new_ops.extend([eq_and_tie, pick_lhs, ord_lt_eq, ord_val, pick, nan_const_int, nan_const_float, result])
        rewriter.replace_op(op, new_ops=new_ops, new_results=[result.result])


class ConvertCmpfOp(RewritePattern):
    """
    Lower arith.cmpf(predicate, a, b) via hardfloat.compare_rec_fn.

    The compare op returns (lt, eq, gt) where all three are 0 iff a or b is NaN.
    So `ord = lt | eq | gt` and `uno = !ord`. Each predicate maps to a boolean
    combination over (lt, eq, gt, uno).
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: arith.CmpfOp, rewriter: PatternRewriter):
        in_type = cast(AnyFloat, op.lhs.type)
        if type(in_type) not in _type_mapping:
            return
        exp_width, sig_width = _type_mapping[type(in_type)]
        bitwidth = in_type.bitwidth
        predicate = op.predicate.value.data

        new_ops: list[Operation] = []

        if predicate == 0:  # false
            const = hw.ConstantOp(0, 1)
            new_ops.append(const)
            rewriter.replace_op(op, new_ops=new_ops, new_results=[const.result])
            return
        if predicate == 15:  # true
            const = hw.ConstantOp(1, 1)
            new_ops.append(const)
            rewriter.replace_op(op, new_ops=new_ops, new_results=[const.result])
            return

        cast_lhs = UnrealizedConversionCastOp.get([op.lhs], [IntegerType(bitwidth)])
        cast_rhs = UnrealizedConversionCastOp.get([op.rhs], [IntegerType(bitwidth)])
        recode_lhs = FnToRecFnOp([cast_lhs], [IntegerType(bitwidth + 1)], sig_width, exp_width)
        recode_rhs = FnToRecFnOp([cast_rhs], [IntegerType(bitwidth + 1)], sig_width, exp_width)
        signaling = hw.ConstantOp(0, 1)
        cmp = CompareRecFnOp(
            [recode_lhs, recode_rhs, signaling],
            [IntegerType(1), IntegerType(1), IntegerType(1), IntegerType(5)],
            sig_width,
            exp_width,
        )
        new_ops.extend([cast_lhs, cast_rhs, recode_lhs, recode_rhs, signaling, cmp])

        lt, eq, gt, _flags = cmp.results

        def or_(a: SSAValue, b: SSAValue) -> SSAValue:
            o = arith.OrIOp(a, b)
            new_ops.append(o)
            return o.result

        # Ordered = lt | eq | gt; Unordered = !ord
        ord_val = or_(or_(lt, eq), gt)
        one_i1 = hw.ConstantOp(1, 1)
        new_ops.append(one_i1)
        uno_xor = arith.XOrIOp(ord_val, one_i1.result)
        new_ops.append(uno_xor)
        uno = uno_xor.result

        match predicate:
            case 1:  # oeq
                result = eq
            case 2:  # ogt
                result = gt
            case 3:  # oge
                result = or_(gt, eq)
            case 4:  # olt
                result = lt
            case 5:  # ole
                result = or_(lt, eq)
            case 6:  # one
                result = or_(lt, gt)
            case 7:  # ord
                result = ord_val
            case 8:  # ueq
                result = or_(eq, uno)
            case 9:  # ugt
                result = or_(gt, uno)
            case 10:  # uge
                result = or_(or_(gt, eq), uno)
            case 11:  # ult
                result = or_(lt, uno)
            case 12:  # ule
                result = or_(or_(lt, eq), uno)
            case 13:  # une
                not_eq = arith.XOrIOp(eq, one_i1.result)
                new_ops.append(not_eq)
                result = not_eq.result
            case 14:  # uno
                result = uno
            case _:
                raise NotImplementedError(f"Unhandled cmpf predicate {predicate}")

        rewriter.replace_op(op, new_ops=new_ops, new_results=[result])


class ConvertFloatToHardfloatPass(ModulePass):
    name = "convert-float-to-hardfloat"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [
                    ConvertAddSubOp(),
                    ConvertMulOp(),
                    ConvertIToFPOp(),
                    ConvertFPToIOp(),
                    ConvertCmpfOp(),
                    ConvertMaximumMinimumOp(),
                    ConvertTruncExtfOp(),
                    ConvertFmaOp(),
                ]
            ),
            apply_recursively=False,
        ).rewrite_module(op)

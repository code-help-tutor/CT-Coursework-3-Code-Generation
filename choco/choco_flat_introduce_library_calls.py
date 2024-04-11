WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
# type: ignore

from ast import IfExp
from choco.dialects.choco_flat import *
from choco.dialects.choco_type import *
from riscv.ssa_dialect import *

from dataclasses import dataclass, field
from xdsl.printer import Printer
from xdsl.ir import Operation, BlockArgument, MLContext, Region, Block, SSAValue, OpResult
from xdsl.dialects.builtin import ModuleOp
from xdsl.pattern_rewriter import RewritePattern, PatternRewriter, PatternRewriteWalker, GreedyRewritePatternApplier, op_type_rewrite_pattern
from typing import Dict, List, Tuple, Optional

from choco.dialects.choco_type import ListType, int_type, str_type, bool_type, none_type


@dataclass(eq=False)
class CallExprPattern(RewritePattern):
    """
    Rewrite a choco flat program into a RISCV SSA program.
    """

    ctx: MLContext

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: CallExpr, rewriter: PatternRewriter):
        if op.func_name.data == 'input':
            call = CallExpr.create(
                operands=[],
                result_types=[str_type],
                attributes={"func_name": StringAttr.from_str("_input")})
            rewriter.replace_op(op, [call], [call.results[0]])
            return

        if op.func_name.data != 'print':
            return

        if op.operands[0].typ == bool_type:
            call = CallExpr.create(
                operands=op.operands,
                attributes={"func_name": StringAttr.from_str("_print_bool")})
            rewriter.replace_op(op, [call])
            return

        if op.operands[0].typ == int_type:
            call = CallExpr.create(
                operands=op.operands,
                attributes={"func_name": StringAttr.from_str("_print_int")})
            rewriter.replace_op(op, [call])
            return

        if op.operands[0].typ == str_type:
            call = CallExpr.create(
                operands=op.operands,
                attributes={"func_name": StringAttr.from_str("_print_str")})
            rewriter.replace_op(op, [call])
            return

        raise Exception(
            "Type Error: Cannot print an object of type different than bool, int, or str"
        )


@dataclass(eq=False)
class BinaryExprPattern(RewritePattern):
    """
    Rewrite certain binary expressions to function calls provides as part of
    the runtime library.
    """

    ctx: MLContext

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: BinaryExpr, rewriter: PatternRewriter):
        if op.op.data == "+" and (type(op.results[0].typ) == ListType
                                  or op.results[0].typ == str_type):
            call = CallExpr.create(
                operands=op.operands,
                result_types=[op.results[0].typ],
                attributes={"func_name": StringAttr.from_str("_list_concat")})
            rewriter.replace_op(op, [call])

        if op.op.data == "==" and op.lhs.typ == str_type:
            call = CallExpr.create(
                operands=op.operands,
                result_types=[op.result.typ],
                attributes={"func_name": StringAttr.from_str("_str_eq")})
            rewriter.replace_op(op, [call])

        if op.op.data == "!=" and op.lhs.typ == str_type:
            call = CallExpr.create(
                operands=op.operands,
                result_types=[op.result.typ],
                attributes={"func_name": StringAttr.from_str("_str_eq")})
            complement = UnaryExpr.build(operands=[call],
                                         attributes={"op": "not"},
                                         result_types=[op.result.typ])
            rewriter.replace_op(op, [call, complement])


def choco_flat_introduce_library_calls(ctx: MLContext, op: ModuleOp):
    walker = PatternRewriteWalker(GreedyRewritePatternApplier([
        CallExprPattern(ctx),
        BinaryExprPattern(ctx),
    ]),
                                  apply_recursively=False)

    walker.rewrite_module(op)

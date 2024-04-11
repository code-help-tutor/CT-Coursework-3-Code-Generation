WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from xdsl.dialects.builtin import ModuleOp, IntegerAttr
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.pattern_rewriter import (GreedyRewritePatternApplier,
                                   PatternRewriter, PatternRewriteWalker,
                                   RewritePattern, op_type_rewrite_pattern)

from choco.dialects.choco_flat import *
from choco.dialects.choco_type import *


@dataclass
class LiteralRewriter(RewritePattern):

    @op_type_rewrite_pattern
    def match_and_rewrite(  # type: ignore reportIncompatibleMethodOverride
            self, literal: Literal, rewriter: PatternRewriter) -> None:
        if len(literal.results[0].uses) == 0:
            rewriter.replace_op(literal, [], [None])
        return


@dataclass
class BinaryExprRewriter(RewritePattern):

    @op_type_rewrite_pattern
    def match_and_rewrite(  # type: ignore reportIncompatibleMethodOverride
            self, expr: BinaryExpr, rewriter: PatternRewriter) -> None:
        if expr.parent and expr.parent.parent and expr.parent.parent.parent and isinstance(
                expr.parent.parent.parent, While):
            return
        if len(expr.results[0].uses) == 0:
            rewriter.replace_op(expr, [], [None])
        return


def choco_flat_dead_code_elimination(ctx: MLContext,
                                     module: ModuleOp) -> ModuleOp:
    walker = PatternRewriteWalker(GreedyRewritePatternApplier([
        LiteralRewriter(),
        BinaryExprRewriter(),
    ]),
                                  walk_reverse=True)
    walker.rewrite_module(module)

    return module

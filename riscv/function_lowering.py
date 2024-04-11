WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
# type: ignore

from __future__ import annotations

import riscv.dialect as riscv
from riscv.dialect import RegisterAttr, Register
import riscv.ssa_dialect as riscvssa

from xdsl.ir import Operation, SSAValue, Block, MLContext
from xdsl.pattern_rewriter import RewritePattern, PatternRewriter, GreedyRewritePatternApplier, PatternRewriteWalker
from xdsl.dialects.builtin import ModuleOp

from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict


@dataclass(eq=False)
class FunctionPattern(RewritePattern):
    """
    """

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):
        if not isinstance(op, riscvssa.FuncOp):
            return

        block_before = Block()
        block_before.add_op(riscv.LabelOp.get(op.func_name.data))
        block_after = Block()
        rewriter.inline_block_after(block_before, op)
        rewriter.inline_block_after(op.func_body.blocks[0], op)
        rewriter.inline_block_after(block_after, op)
        rewriter.erase_op(op)


def riscv_function_lowering(ctx: MLContext, mod: ModuleOp):
    walker = PatternRewriteWalker(GreedyRewritePatternApplier(
        [FunctionPattern()]),
                                  apply_recursively=True,
                                  walk_reverse=True)
    walker.rewrite_module(mod)
    jump = riscv.JALOp.get(Register.from_name("ra"), "_main")
    jump.parent = mod.regions[0].blocks[0]
    mod.regions[0].blocks[0].ops = [jump] + mod.ops

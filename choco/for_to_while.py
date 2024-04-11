WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation, SSAValue, Region
from xdsl.dialects.builtin import IntegerAttr, StringAttr
from xdsl.pattern_rewriter import (GreedyRewritePatternApplier,
                                   PatternRewriter, PatternRewriteWalker,
                                   RewritePattern, op_type_rewrite_pattern)

from choco.dialects.choco_flat import *


@dataclass
class ForLoopRewriter(RewritePattern):
    """
    Rewrite:
        for x in {expr}:
            {body}
    into:
        itr = {expr}
        idx = 0
        while idx < len(itr):
            x = itr[idx]
            {body}
            idx = idx + 1
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(  # type: ignore reportIncompatibleMethodOverride
            self, for_loop: For, rewriter: PatternRewriter):
        x = for_loop.iter_
        itr = for_loop.target
        assert isinstance(x, SSAValue)
        assert isinstance(itr, SSAValue)
        # idx = 0
        idx_mem = Alloc.create(
            attributes={"type": choco_type.int_type},
            result_types=[MemlocType([choco_type.int_type])])
        zero = Literal.create(
            attributes={"value": IntegerAttr.from_int_and_width(0, 32)},
            result_types=[choco_type.int_type])
        idx_store = Store.build(operands=[idx_mem.results[0], zero.results[0]])

        # build conditional region
        len_call = CallExpr.create(
            operands=[itr],
            attributes={"func_name": StringAttr.from_str("len")},
            result_types=[choco_type.int_type])
        idx0 = Load.create(operands=[idx_mem.results[0]],
                           result_types=[choco_type.int_type])
        binary_expr = BinaryExpr.create(
            attributes={"op": StringAttr.from_str("<")},
            operands=[idx0.results[0], len_call.results[0]],
            result_types=[choco_type.bool_type])
        cond = Region.from_operation_list([
            len_call, idx0, binary_expr,
            Yield.build(operands=[binary_expr.results[0]])
        ])

        # build body region
        # x = itr[idx]
        idx1 = Load.create(operands=[idx_mem.results[0]],
                           result_types=[choco_type.int_type])
        header: list[Operation] = [idx1]
        if itr.typ == str_type:
            elem_addr = GetAddress.create(
                operands=[itr, idx1.results[0]],
                result_types=[MemlocType([str_type])])  # type: ignore
            elem_load = Load.create(
                operands=[elem_addr.results[0]],
                result_types=[
                    elem_addr.results[0].typ.type  # type: ignore
                ])  # type: ignore
            str_constr = ListExpr.build(operands=[[elem_load.results[0]]],
                                        result_types=[str_type])

            header += [elem_addr, elem_load, str_constr]
        else:
            elem_addr = GetAddress.create(operands=[itr, idx1.results[0]],
                                          result_types=[x.typ])  # type: ignore
            elem_load = Load.create(
                operands=[elem_addr.results[0]],
                result_types=[
                    elem_addr.results[0].typ.type  # type: ignore
                ])  # type: ignore
            header += [elem_addr, elem_load]

        store = Store.build(operands=[x, header[-1]])
        header += [store]
        # idx = idx + 1
        one = Literal.create(
            attributes={"value": IntegerAttr.from_int_and_width(1, 32)},
            result_types=[choco_type.int_type])
        idx2 = Load.create(operands=[idx_mem.results[0]],
                           result_types=[choco_type.int_type])
        idx_plus_one = BinaryExpr.create(
            attributes={"op": StringAttr.from_str("+")},
            operands=[idx2.results[0], one.results[0]],
            result_types=[choco_type.int_type])
        footer: list[Operation] = [
            idx2, one, idx_plus_one,
            Store.build(operands=[idx_mem.results[0], idx_plus_one])
        ]
        body = Region.from_operation_list(header)
        for op in for_loop.body.ops:
            op.detach()
            body.blocks[0].add_op(op)
        body.blocks[0].add_ops(footer)

        while_loop = While.create(regions=[cond, body])

        rewriter.replace_op(for_loop, [idx_mem, zero, idx_store, while_loop])


def for_to_while(ctx: MLContext, module: ModuleOp) -> ModuleOp:
    walker = PatternRewriteWalker(GreedyRewritePatternApplier([
        ForLoopRewriter(),
    ]),
                                  apply_recursively=False)
    walker.rewrite_module(module)

    return module

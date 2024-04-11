WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from __future__ import annotations
from xdsl.dialects.builtin import StringAttr, ModuleOp, IntegerAttr
from xdsl.ir import Operation, Attribute, ParametrizedAttribute, Region, Block, SSAValue, MLContext, OpResult
from xdsl.printer import Printer

from util.list_ops import flatten
from choco.dialects import choco_flat, choco_ast, choco_type
from choco.type_checking import join, Type, to_attribute
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from choco.dialects.choco_flat import Assign, GetAddress, IndexString, ListExpr, Yield, Alloc, Store, Load, MemlocType


@dataclass
class SSAValueCtx:
    """
    Context that relates identifiers from the AST to SSA values used in the flat representation.
    """
    dictionary: Dict[str, SSAValue] = field(default_factory=dict)
    parent_scope: Optional[SSAValueCtx] = None

    def __getitem__(self, identifier: str) -> Optional[SSAValue]:
        """Check if the given identifier is in the current scope, or a parent scope"""
        ssa_value = self.dictionary.get(identifier, None)
        if ssa_value:
            return ssa_value
        elif self.parent_scope:
            return self.parent_scope[identifier]
        else:
            return None

    def __setitem__(self, identifier: str, ssa_value: SSAValue):
        """Relate the given identifier and SSA value in the current scope"""
        if identifier in self.dictionary:
            raise Exception()
        else:
            self.dictionary[identifier] = ssa_value


def choco_ast_to_choco_flat(ctx: MLContext, input_module: ModuleOp):
    input_program = input_module.ops[0]
    assert isinstance(input_program, choco_ast.Program)
    res_module = translate_program(input_program)
    res_module.regions[0].move_blocks(input_module.regions[0])
    move_free_ops_into_main(ctx, input_module)


def move_free_ops_into_main(ctx: MLContext, module: ModuleOp):
    body = Region()
    block = Block()
    for op in module.ops:
        # TODO: clearly we do not want to have nested functions, but this was the easiest way to
        #       keep the current end-to-end tests working ...
        # if not isinstance(op, choco_flat.FuncDef):
        op.detach()
        block.add_ops([op])
    body.add_block(block)
    main = choco_flat.FuncDef.create(attributes={
        "func_name": StringAttr.from_str("_main"),
        "return_type": choco_type.none_type
    },
                                     regions=[body])
    module.regions[0].blocks[0].add_ops([main])


def translate_program(p: choco_ast.Program) -> ModuleOp:
    # create an empty global context
    global_ctx = SSAValueCtx()
    # first translate all var definitions
    nested_var_defs: List[List[Operation]] = [
        translate_def(global_ctx, op) for op in p.defs.ops
        if isinstance(op, choco_ast.VarDef)
    ]
    # then translate all func definitions
    nested_func_defs: List[List[Operation]] = [
        translate_def(global_ctx, op) for op in p.defs.ops
        if isinstance(op, choco_ast.FuncDef)
    ]
    defs: List[Operation] = flatten(nested_var_defs) + flatten(
        nested_func_defs)
    # then translate all statements
    nested_stms: List[List[Operation]] = [
        translate_stmt(global_ctx, op) for op in p.stmts.blocks[0].ops
    ]
    stms: List[Operation] = flatten(nested_stms)
    return ModuleOp.from_region_or_ops(defs + stms)


def translate_def_or_stmt(ctx: SSAValueCtx, op: Operation) -> List[Operation]:
    """
    Translate an operation that can either be a definition or statement
    """
    # first try to translate op as a definition:
    #   if op is a definition this will return a list of translated Operations
    ops = try_translate_def(ctx, op)
    if ops is not None:
        return ops
    # op has not been a definition, try to translate op as a statement:
    #   if op is a statement this will return a list of translated Operations
    ops = try_translate_stmt(ctx, op)
    if ops is not None:
        return ops
    # operation must have been translated by now
    raise Exception(f"Could not translate `{op}' as a definition or statement")


def try_translate_def(ctx: SSAValueCtx,
                      op: Operation) -> Optional[List[Operation]]:
    """
    Tries to translate op as a definition.
    Returns a list of the translated Operations if op is a definition, returns None otherwise.
    """
    if isinstance(op, choco_ast.FuncDef):
        return [translate_fun_def(ctx, op)]
    elif isinstance(op, choco_ast.VarDef):
        return translate_var_def(ctx, op)
    else:
        return None


def translate_def(ctx: SSAValueCtx, op: Operation) -> List[Operation]:
    """
    Translates op as a definition.
    Returns a list of the translated Operations if op is a definition, fails otherwise.
    """
    ops = try_translate_def(ctx, op)
    if ops is None:
        raise Exception(f"Could not translate `{op}' as a definition")
    else:
        return ops


def translate_fun_def(ctx: SSAValueCtx,
                      fun_def: choco_ast.FuncDef) -> Operation:
    func_name = fun_def.attributes["func_name"]

    def get_param(op: Operation) -> Tuple[str, Attribute]:
        assert isinstance(op, choco_ast.TypedVar)
        var_name = op.attributes.get('var_name')
        assert isinstance(var_name, StringAttr)
        name = var_name.data
        type_name = op.regions[0].blocks[0].ops[0]
        type = try_translate_type(type_name)
        assert type is not None
        return name, type

    params = [get_param(op) for op in fun_def.params.blocks[0].ops]
    param_names: List[str] = [p[0] for p in params]
    param_types: List[Attribute] = [p[1] for p in params]
    return_type = try_translate_type(fun_def.return_type.blocks[0].ops[0])
    if return_type is None:
        return_type = choco_type.none_type

    body = Region()
    block = Block.from_arg_types(param_types)
    # create a new nested scope and
    # relate parameter identifiers with SSA values of block arguments

    # use the nested scope when translate the body of the function
    allocs: List[SSAValue] = []
    for arg in reversed(block.args):
        # alloc space on the local stack for the parameter
        alloc = Alloc.build(attributes={"type": arg.typ},
                            result_types=[MemlocType([arg.typ])])
        allocs.append(alloc.memloc)  #type: ignore
        # update all uses of the parameter with the allocated memory location
        uses = arg.uses.copy()
        # take a copy of the current uses, as we are modifying the uses as we iterate
        for use in uses:
            use.operation.replace_operand(use.index, alloc.results[0])
        # store the passed parameter value into the allocated memory location
        store = Store.build(operands=[alloc, arg])
        block.add_ops([alloc, store])
    c = SSAValueCtx(dictionary=dict(zip(param_names, reversed(allocs))),
                    parent_scope=ctx)
    block.add_ops(
        flatten([
            translate_def_or_stmt(c, op)
            for op in fun_def.func_body.blocks[0].ops
        ]))
    body.add_block(block)

    return choco_flat.FuncDef.create(attributes={
        "func_name": func_name,
        "return_type": return_type
    },
                                     regions=[body])


def try_translate_type(op: Operation) -> Optional[Attribute]:
    """Tries to translate op as a type, returns None otherwise."""
    if isinstance(op, choco_ast.TypeName):
        type_name = op.type_name
        if type_name.data == "int":  #type: ignore
            return choco_type.int_type
        if type_name.data == "bool":  #type: ignore
            return choco_type.bool_type
        if type_name.data == "object":  #type: ignore
            return choco_type.object_type
        if type_name.data == "str":  #type: ignore
            return choco_type.str_type

    if isinstance(op, choco_ast.ListType):
        element_type = try_translate_type(op.regions[0].blocks[0].ops[0])
        assert element_type is not None
        return choco_type.ListType([element_type])

    return None


def translate_var_def(ctx: SSAValueCtx,
                      var_def: choco_ast.VarDef) -> List[Operation]:
    typed_var = var_def.typed_var.blocks[0].ops[0]
    assert isinstance(typed_var, choco_ast.TypedVar)
    var_name = typed_var.attributes["var_name"]
    assert isinstance(var_name, StringAttr)
    type = try_translate_type(typed_var.type.blocks[0].ops[0])
    assert type is not None

    init, init_name = translate_expr(ctx, var_def.literal.blocks[0].ops[0])
    alloc = Alloc.build(attributes={"type": type},
                        result_types=[MemlocType([type])])
    store = Store.build(operands=[alloc, init_name])

    # relate variable identifier and SSA value by adding it into the current context
    ctx[var_name.data] = alloc.results[0]

    return init + [alloc, store]


def try_translate_expr(
    ctx: SSAValueCtx,
    op: Operation,
) -> Optional[Tuple[List[Operation], SSAValue]]:
    """
    Tries to translate op as an expression.
    If op is an expression, returns a list of the translated Operations
    and the ssa value representing the translated expression.
    Returns None otherwise.
    """
    if isinstance(op, choco_ast.Literal):
        op = translate_literal(op)
        return [op], op.results[0]
    if isinstance(op, choco_ast.ExprName):
        ssa_value = ctx[op.id.data]  #type: ignore
        assert isinstance(ssa_value, SSAValue)
        return [], ssa_value
    if isinstance(op, choco_ast.UnaryExpr):
        return translate_unary_expr(ctx, op)
    if isinstance(op, choco_ast.BinaryExpr):
        return translate_binary_expr(ctx, op)
    if isinstance(op, choco_ast.CallExpr):
        return translate_call_expr(ctx, op)
    if isinstance(op, choco_ast.IfExpr):
        return translate_if_expr(ctx, op)
    if isinstance(op, choco_ast.ListExpr):
        return translate_list_expr(ctx, op)
    if isinstance(op, choco_ast.IndexExpr):
        return translate_index_expr(ctx, op)

    assert False, "Unknown Expression"


def translate_expr(ctx: SSAValueCtx,
                   op: Operation,
                   add_load=True) -> Tuple[List[Operation], SSAValue]:
    """
    Translates op as an expression.
    If op is an expression, returns a list of the translated Operations
    and the ssa value representing the translated expression.
    Fails otherwise.
    """
    res = try_translate_expr(ctx, op)
    if res is None:
        raise Exception(f"Could not translate `{op}' as an expression")
    else:
        ops, ssa_value = res
        if add_load and isinstance(ssa_value.typ, MemlocType):
            load = Load.build(
                operands=[ssa_value.op],  #type: ignore
                result_types=[ssa_value.typ.type])  #type: ignore
            return ops + [load], load.result  #type: ignore

        return ops, ssa_value


def translate_literal(op: choco_ast.Literal) -> Operation:
    value = op.attributes["value"]

    if isinstance(value, IntegerAttr):
        return choco_flat.Literal.create(attributes={"value": value},
                                         result_types=[choco_type.int_type])
    if isinstance(value, choco_ast.NoneAttr):
        return choco_flat.Literal.create(
            attributes={"value": choco_flat.NoneAttr()},
            result_types=[choco_type.none_type])

    if isinstance(value, choco_ast.BoolAttr):
        attr = choco_flat.BoolAttr(value.data)  # type: ignore
        return choco_flat.Literal.create(attributes={"value": attr},
                                         result_types=[choco_type.bool_type])
    if isinstance(value, StringAttr):
        return choco_flat.Literal.create(attributes={"value": value},
                                         result_types=[choco_type.str_type])
    raise Exception(f"Could not translate `{op}' as a literal")


def translate_unary_expr(
        ctx: SSAValueCtx,
        unary_expr: choco_ast.UnaryExpr) -> Tuple[List[Operation], SSAValue]:
    value, ssa_value = translate_expr(ctx, unary_expr.value.blocks[0].ops[0])
    attr = unary_expr.op
    assert isinstance(attr, Attribute)
    flat_unary_expr = choco_flat.UnaryExpr.create(attributes={"op": attr},
                                                  operands=[ssa_value],
                                                  result_types=[ssa_value.typ])
    return value + [flat_unary_expr], flat_unary_expr.results[0]


def translate_binary_expr(
        ctx: SSAValueCtx,
        binary_expr: choco_ast.BinaryExpr) -> Tuple[List[Operation], SSAValue]:
    lhs, lhs_ssa_value = translate_expr(ctx, binary_expr.lhs.blocks[0].ops[0])
    rhs, rhs_ssa_value = translate_expr(ctx, binary_expr.rhs.blocks[0].ops[0])
    result_type = rhs_ssa_value.typ

    # list append, lhs rhs different type -> object type
    if (binary_expr.op.data == '+'  #type: ignore
            and lhs_ssa_value.typ != rhs_ssa_value.typ
            and isinstance(lhs_ssa_value.typ, choco_type.ListType)
            and isinstance(rhs_ssa_value.typ, choco_type.ListType)):
        result_type = choco_type.ListType([choco_type.object_type])
    elif binary_expr.op.data != "is":  #type: ignore
        assert lhs_ssa_value.typ == rhs_ssa_value.typ

    if binary_expr.op.data in [  #type: ignore
            '!=', '==', '<', '<=', '>', '>=', 'is'
    ]:
        result_type = choco_type.bool_type

    attr = binary_expr.op
    assert isinstance(attr, Attribute)

    # Special case when the binary operation has a different execution order
    if binary_expr.op.data in ['or', 'and']:  #type: ignore
        lhs.append(Yield.get(lhs_ssa_value))
        rhs.append(Yield.get(rhs_ssa_value))
        flat_binary_expr = choco_flat.EffectfulBinaryExpr.build(
            attributes={"op": attr},
            regions=[lhs, rhs],
            result_types=[result_type])
        return [flat_binary_expr], flat_binary_expr.results[0]

    flat_binary_expr = choco_flat.BinaryExpr.create(
        attributes={"op": attr},
        operands=[lhs_ssa_value, rhs_ssa_value],
        result_types=[result_type])
    return lhs + rhs + [flat_binary_expr], flat_binary_expr.results[0]


def translate_if_expr(
        ctx: SSAValueCtx,
        if_expr: choco_ast.IfExpr) -> Tuple[List[Operation], SSAValue]:
    cond, cond_name = translate_expr(ctx, if_expr.cond.blocks[0].ops[0])
    then, then_name = translate_expr(ctx, if_expr.then.blocks[0].ops[0])
    or_else, or_else_name = translate_expr(ctx,
                                           if_expr.or_else.blocks[0].ops[0])

    then.append(choco_flat.Yield.build(operands=[then_name]))
    or_else.append(choco_flat.Yield.build(operands=[or_else_name]))
    flat_if_expr = choco_flat.IfExpr.create(
        operands=[cond_name],
        regions=[
            Region.from_operation_list(then),
            Region.from_operation_list(or_else)
        ],
        result_types=[then_name.typ])
    return cond + [flat_if_expr], flat_if_expr.results[0]


def translate_list_expr(
        ctx: SSAValueCtx,
        list_expr: choco_ast.ListExpr) -> Tuple[List[Operation], SSAValue]:
    ops: List[Operation] = []
    ops_names: List[SSAValue] = []
    for region in list_expr.elems.blocks[0].ops:
        op, op_name = translate_expr(ctx, region)
        ops += op
        ops_names.append(op_name)

    if len(ops_names) > 0:
        res_type = Type.from_attribute(ops_names[0].typ)
        for op in ops_names:
            res_type = join(res_type, Type.from_attribute(op.typ))
        result_type = choco_type.ListType([to_attribute(res_type)])
    else:
        result_type = choco_type.empty_type
    flat_list_expr = choco_flat.ListExpr.create(operands=ops_names,
                                                result_types=[result_type])
    return ops + [flat_list_expr], flat_list_expr.results[0]


def translate_index_expr(
        ctx: SSAValueCtx,
        index_expr: choco_ast.IndexExpr) -> Tuple[List[Operation], SSAValue]:
    value, value_name = translate_expr(ctx, index_expr.value.blocks[0].ops[0])
    index, index_name = translate_expr(ctx, index_expr.index.blocks[0].ops[0])
    assert isinstance(value_name.typ, ParametrizedAttribute)

    ty = value_name.typ
    if isinstance(ty, choco_type.ListType):
        ty = ty.parameters[0]
    else:
        assert ty == choco_type.str_type or isinstance(ty, MemlocType)

    value_typ = value_name.typ  # type: ignore
    if value_typ == choco_type.str_type:
        address = choco_flat.IndexString.build(
            operands=[value_name, index_name],
            result_types=[MemlocType([choco_type.str_type])])
    elif isinstance(value_typ, choco_flat.ListType):
        address = choco_flat.GetAddress.build(
            operands=[value_name, index_name],
            result_types=[MemlocType([value_typ.elem_type])])
    else:
        raise Exception("Unknown type for the value of index expression")

    return value + index + [address], address.results[0]


def translate_call_expr(
        ctx: SSAValueCtx,
        call_expr: choco_ast.CallExpr) -> Tuple[List[Operation], SSAValue]:
    ops: List[Operation] = []
    args: List[SSAValue] = []

    for arg in call_expr.args.blocks[0].ops:
        op, arg = translate_expr(ctx, arg)
        ops += op
        args.append(arg)

    name = call_expr.attributes["func"]
    #print((call_expr))
    call = choco_flat.CallExpr.create(
        attributes={"func_name": name},
        operands=args,
        result_types=[call_expr.attributes["type_hint"]])
    ops.append(call)
    return ops, call.results[0]


# This function could be avoided if we could remove the result type via rewriting in a separate pass
def translate_call_expr_stmt(ctx: SSAValueCtx,
                             call_expr: choco_ast.CallExpr) -> List[Operation]:
    ops: List[Operation] = []
    args: List[SSAValue] = []

    for arg in call_expr.args.blocks[0].ops:
        op, arg = translate_expr(ctx, arg)
        ops += op
        args.append(arg)

    name = call_expr.attributes["func"]
    call = choco_flat.CallExpr.create(attributes={"func_name": name},
                                      operands=args)
    ops.append(call)
    return ops


def try_translate_stmt(ctx: SSAValueCtx,
                       op: Operation) -> Optional[List[Operation]]:
    """
    Tries to translate op as a statement.
    If op is an expression, returns a list of the translated Operations.
    Returns None otherwise.
    """
    if isinstance(op, choco_ast.Assign):
        return translate_assign(ctx, op)
    if isinstance(op, choco_ast.Return):
        return translate_return(ctx, op)
    if isinstance(op, choco_ast.CallExpr):
        return translate_call_expr_stmt(ctx, op)
    if isinstance(op, choco_ast.Pass):
        return translate_pass(ctx, op)
    if isinstance(op, choco_ast.If):
        return translate_if(ctx, op)
    if isinstance(op, choco_ast.While):
        return translate_while(ctx, op)
    if isinstance(op, choco_ast.For):
        return translate_for(ctx, op)
    if isinstance(op, choco_ast.GlobalDecl):
        return translate_global_decl(ctx, op)

    res = try_translate_expr(ctx, op)
    if res is None:
        return None
    else:
        return res[0]


def translate_stmt(ctx: SSAValueCtx, op: Operation) -> List[Operation]:
    """
    Translates op as a statement.
    If op is an expression, returns a list of the translated Operations.
    Fails otherwise.
    """
    ops = try_translate_stmt(ctx, op)
    if ops is None:
        raise Exception(f"Could not translate `{op}' as a statement")
    else:
        return ops


def split_multi_assign(
        assign: choco_ast.Assign) -> Tuple[List[Operation], Operation]:
    """Get the list of targets of a multi assign, as well as the expression value."""
    if isinstance(assign.value.op, choco_ast.Assign):
        targets, value = split_multi_assign(assign.value.op)
        return [assign.target.op] + targets, value
    return [assign.target.op], assign.value.op


def translate_assign(ctx: SSAValueCtx,
                     assign: choco_ast.Assign) -> List[Operation]:
    targets, value = split_multi_assign(assign)
    value_flat, value_var = translate_expr(ctx, value)
    translated_targets = [
        translate_expr(ctx, target, add_load=False) for target in targets
    ]
    target_ops: List[Operation] = []
    for target_flat, target_var in translated_targets:
        assert isinstance(target_var.typ, MemlocType)
        target_ops += target_flat
        target_ops.append(Store.build(operands=[target_var, value_var]))

    return value_flat + target_ops


def translate_return(ctx: SSAValueCtx,
                     ret: choco_ast.Return) -> List[Operation]:
    ops = ret.value.blocks[0].ops
    if len(ops) == 0:
        none = choco_flat.Literal.create(
            attributes={"value": choco_flat.NoneAttr()},
            result_types=[choco_type.none_type])
        return [none, choco_flat.Return.create(operands=[none.results[0]])]

    value, value_name = translate_expr(ctx, ops[0])
    return value + [choco_flat.Return.create(operands=[value_name])]


def translate_pass(ctx: SSAValueCtx,
                   pass_stmt: choco_ast.Pass) -> List[Operation]:
    return []


def translate_if(ctx: SSAValueCtx, if_stmt: choco_ast.If) -> List[Operation]:
    cond, cond_name = translate_expr(ctx, if_stmt.cond.blocks[0].ops[0])

    ops: List[Operation] = []
    for op in if_stmt.then.blocks[0].ops:
        stmt_ops = translate_stmt(ctx, op)
        ops += stmt_ops
    then = Region.from_operation_list(ops)

    ops: List[Operation] = []
    for op in if_stmt.orelse.blocks[0].ops:
        stmt_ops = translate_stmt(ctx, op)
        ops += stmt_ops
    orelse = Region.from_operation_list(ops)

    new_op = choco_flat.If.build(operands=[cond_name], regions=[then, orelse])
    return cond + [new_op]


def translate_while(ctx: SSAValueCtx,
                    while_stmt: choco_ast.While) -> List[Operation]:
    ops: List[Operation] = []
    stmt_ops, stmt_name = translate_expr(ctx, while_stmt.cond.ops[0])
    stmt_ops.append(choco_flat.Yield.build(operands=[stmt_name]))
    cond = Region.from_operation_list(stmt_ops)

    ops: List[Operation] = []
    for op in while_stmt.body.blocks[0].ops:
        stmt_ops = translate_stmt(ctx, op)
        ops += stmt_ops
    body = Region.from_operation_list(ops)

    new_op = choco_flat.While.build(operands=[], regions=[cond, body])
    return [new_op]


def translate_for(ctx: SSAValueCtx,
                  for_stmt: choco_ast.For) -> List[Operation]:
    target, target_name = translate_expr(ctx, for_stmt.iter.blocks[0].ops[0])

    ops: List[Operation] = []
    for op in for_stmt.body.blocks[0].ops:
        stmt_ops = translate_stmt(ctx, op)
        ops += stmt_ops
    body = Region.from_operation_list(ops)

    iterator = ctx[for_stmt.iter_name.data]  #type: ignore
    new_op = choco_flat.For.build(operands=[iterator, target_name],
                                  regions=[body])
    return target + [new_op]


def translate_global_decl(
        ctx: SSAValueCtx,
        global_decl: choco_ast.GlobalDecl) -> List[Operation]:
    # Global declarations have no use in the flat IR. They are used to
    # communicate the programmers intention to write to global variables.
    # In the IR, this fact is already communicated by the presence of
    # writes to such varibables and does not require a redundant
    # encoding that is purely meant to catch programming errors.
    return []

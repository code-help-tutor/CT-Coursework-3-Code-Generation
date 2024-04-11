WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from functools import reduce
from typing import Dict, List, Optional, Tuple, Union

from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import MLContext, Operation, Attribute
from choco.ast_visitor import Visitor
from choco.dialects import choco_ast, choco_type
from choco.semantic_error import SemanticError


class Type(ABC):

    @staticmethod
    def from_op(op: Operation) -> 'Type':
        if isinstance(op, choco_ast.TypeName):
            name = op.type_name.data  #type: ignore
            if name == "int":
                return int_type
            if name == "bool":
                return bool_type
            if name == "str":
                return str_type
            if name == "<None>":
                return none_type
            if name == "<Empty>":
                return empty_type
            if name == "object":
                return object_type
            raise Exception(f"Found type with unknown name `{name}'")
        if isinstance(op, choco_ast.ListType):
            elem_type = Type.from_op(op.elem_type.op)
            return ListType(elem_type)
        raise Exception(f'Found {op}, expected TypeName or ListType')

    @staticmethod
    def from_attribute(attr: Attribute) -> 'Type':
        if isinstance(attr, choco_type.NamedType):
            name: str = attr.type_name.data  # type: ignore
            if name == "int":
                return int_type
            if name == "bool":
                return bool_type
            if name == "str":
                return str_type
            if name == "<None>":
                return none_type
            if name == "<Empty>":
                return empty_type
            if name == "object":
                return object_type
            raise Exception(f"Found type with unknown name `{name}'")
        if isinstance(attr, choco_type.ListType):
            elem_type = Type.from_attribute(attr.elem_type)  # type: ignore
            return ListType(elem_type)
        raise Exception(f'Found {attr}, expected TypeName or ListType')


@dataclass
class BasicType(Type):
    name: str


@dataclass
class ListType(Type):
    elem_type: Type


class BottomType(Type):  # "⊥"
    pass


class ObjectType(Type):  # "object"
    pass


@dataclass
class FunctionType(Type):  # input0 x ... x inputN -> output
    inputs: List[Type]
    output: Type


int_type = BasicType("int")
bool_type = BasicType("bool")
str_type = BasicType("str")
none_type = BasicType("<None>")
empty_type = BasicType("<Empty>")
bottom_type = BottomType()
object_type = ObjectType()


def to_attribute(t: Type) -> Attribute:
    if t == int_type:
        return choco_type.int_type
    elif t == bool_type:
        return choco_type.bool_type
    elif t == str_type:
        return choco_type.str_type
    elif t == none_type:
        return choco_type.none_type
    elif t == empty_type:
        return choco_type.empty_type
    elif t == object_type:
        return choco_type.object_type
    elif isinstance(t, ListType):
        elem_type = to_attribute(t.elem_type)
        return choco_type.ListType([elem_type])
    else:
        raise Exception(f"Can't translate {t} into an attribute")


def join(t1: Type, t2: Type) -> Type:
    if is_assignment_compatible(t1, t2):
        return t2
    if is_assignment_compatible(t2, t1):
        return t1
    else:
        return object_type


def is_subtype(t1: Type, t2: Type) -> bool:
    if t1 == t2:
        return True
    elif t2 == object_type and (t1 == int_type or t1 == bool_type
                                or t1 == str_type or isinstance(t1, ListType)):
        return True
    elif t1 == none_type and t2 == object_type:
        return True
    elif t1 == empty_type and t2 == object_type:
        return True
    elif t1 == bottom_type:
        return True
    else:
        return False


def is_assignment_compatible(t1: Type, t2: Type) -> bool:
    if is_subtype(t1, t2) and t1 != bottom_type:
        return True
    elif (
            t1 == none_type
    ) and t2 != int_type and t2 != bool_type and t2 != str_type and t2 != bottom_type:
        return True
    elif isinstance(t2, ListType) and t1 == empty_type:
        return True
    elif isinstance(t2, ListType) and isinstance(t1, ListType) and \
            t1.elem_type == none_type and \
            is_assignment_compatible(none_type, t2.elem_type):
        return True
    else:
        return False


def check_assignment_compatibility(t1: Type, t2: Type):
    if not is_assignment_compatible(t1, t2):
        raise SemanticError(
            f" Expected {t1} and {t2} to be assignment compatible")


def check_type(found: Type, expected: Type):
    if found != expected:
        raise SemanticError(f"Found `{found}' but expected {expected}")


def check_list_type(found: Type) -> Type:
    if not isinstance(found, ListType):
        raise SemanticError(f"Found `{found}' but expected a list type")
    else:
        return found.elem_type


@dataclass
class FunctionInfo:
    func_type: FunctionType
    params: List[str]
    nested_defs: List[Tuple[str, Type]]

    def __post_init__(self):
        if len(self.func_type.inputs) != len(self.params):
            raise Exception(
                f"Expected same number of input types and parameter names")


LocalEnvironment = Dict[str, Union[Type, FunctionInfo]]


def type_checking(_: MLContext, module: ModuleOp) -> ModuleOp:
    o = build_env(module)
    r = bottom_type

    program = module.ops[0]
    assert isinstance(program, choco_ast.Program)
    if len(program.defs.ops) >= 1:
        check_stmt_or_def_list(o, r, program.defs.ops)
    if len(program.stmts.ops) >= 1:
        check_stmt_or_def_list(o, r, program.stmts.ops)

    return module


# Build local environments
def build_env(module: ModuleOp) -> LocalEnvironment:
    o: LocalEnvironment = {
        "len": FunctionInfo(FunctionType([object_type], int_type), ["arg"],
                            []),
        "print": FunctionInfo(FunctionType([object_type], none_type), ["arg"],
                              []),
        "input": FunctionInfo(FunctionType([], str_type), [], [])
    }

    @dataclass
    class BuildEnvVisitor(Visitor):
        o: LocalEnvironment

        def visit_typed_var(self, typed_var: choco_ast.TypedVar):
            name, type = typed_var.var_name.data, Type.from_op(  #type: ignore
                typed_var.type.op)
            self.o.update({name: type})

        def traverse_func_def(self, func_def: choco_ast.FuncDef):
            f: str = func_def.func_name.data  #type: ignore
            # collect function parameter names and types
            xs: List[str] = []
            ts: List[Type] = []
            for op in func_def.params.ops:
                assert isinstance(op, choco_ast.TypedVar)
                name, type = op.var_name.data, Type.from_op(  #type: ignore
                    op.type.op)
                xs.append(name)
                ts.append(type)
            # collect return type
            t = Type.from_op(func_def.return_type.op) \
                if (len(func_def.return_type.ops) == 1) else none_type
            # collect nested variable definitions
            body_visitor = BuildEnvVisitor({})
            for op in func_def.func_body.ops:
                body_visitor.traverse(op)
            vs: List[Tuple[str, Type]] = []
            for var_name, var_type in body_visitor.o.items():
                assert isinstance(var_type, Type)
                vs.append((var_name, var_type))

            o.update({f: FunctionInfo(FunctionType(ts, t), xs, vs)})

    BuildEnvVisitor(o).traverse(module)

    return o


# Dispatch to typing rules to decide which rule to invoke


def check_stmt_or_def_list(o: LocalEnvironment, r: Type, ops: List[Operation]):
    return stmt_def_list_rule(o, r, ops)


def check_stmt_or_def(o: LocalEnvironment, r: Type, op: Operation):
    if isinstance(op, choco_ast.FuncDef):
        func_def = op
        f = func_def.func_name.data  #type: ignore
        b = func_def.func_body.ops

        return func_def_rule(o, r, f, b)
    elif isinstance(op, choco_ast.VarDef):
        typed_var = op.typed_var.op
        assert isinstance(typed_var, choco_ast.TypedVar)
        id = typed_var.var_name.data  #type: ignore
        e1 = op.literal.op
        return var_init_rule(o, r, id, e1)
    elif isinstance(op, choco_ast.Assign):

        def collect_assignment_targets(
                op: Operation,
                targets: List[Operation]) -> Tuple[List[Operation], Operation]:
            if isinstance(op, choco_ast.Assign):
                return collect_assignment_targets(op.value.op,
                                                  targets + [op.target.op])
            else:
                return targets, op

        targets, value = collect_assignment_targets(op, [])

        # Check if there is only a single assignment
        if len(targets) == 1:
            target = targets[0]
            assign_stmt_rule(o, r, target, value)
            return
        # there are multiple assignments!
        elif len(targets) > 1:
            return multi_assign_stmt(o, r, targets, value)
        else:
            raise Exception("Expected to find at least one assignment target")
    elif isinstance(op, choco_ast.Pass):
        return pass_rule(o, r)
    elif isinstance(op, choco_ast.Return):
        if len(op.value.ops) == 0:
            return return_rule(o, r)
        elif len(op.value.ops) == 1:
            e = op.value.op
            return return_e_rule(o, r, e)
        else:
            assert False
    elif isinstance(op, choco_ast.If):
        e = op.cond.op
        b1 = op.then.ops
        b2 = op.orelse.ops if len(op.orelse.ops) > 0 else None
        return if_else_rule(o, r, e, b1, b2)
    elif isinstance(op, choco_ast.While):
        e = op.cond.op
        b = op.body.ops
        return while_rule(o, r, e, b)
    elif isinstance(op, choco_ast.For):
        e = op.iter.op
        b = op.body.ops
        id = op.iter_name.data  #type: ignore
        t = check_expr(o, r, e)
        if t == str_type:
            return for_str_rule(o, r, id, e, b)
        elif isinstance(t, ListType):
            return for_list_rule(o, r, id, e, b)
        else:
            raise SemanticError(f"Found {t} but expected str or list type")
    elif isinstance(op, choco_ast.GlobalDecl) or isinstance(
            op, choco_ast.NonLocalDecl):
        pass
    else:
        return expr_stmt_rule(o, r, op)


def check_expr(o: LocalEnvironment, r: Type, op: Operation) -> Type:
    t: Optional[Type] = None
    if isinstance(op, choco_ast.Literal):
        t = literal_rules(o, r, op)
    elif isinstance(op, choco_ast.UnaryExpr):
        op_name = op.op.data  #type: ignore
        e = op.value.op
        if op_name == "-":
            t = negate_rule(o, r, e)
        elif op_name == "not":
            t = not_rule(o, r, e)
        else:
            assert False
    elif isinstance(op, choco_ast.BinaryExpr):
        op_name = op.op.data  #type: ignore
        e1 = op.lhs.op
        e2 = op.rhs.op
        if op_name in ["+", "-", "*", "//", "%"]:
            t1 = check_expr(o, r, e1)
            if t1 == int_type:
                t = arith_rule(o, r, e1, op_name, e2)
            elif t1 == str_type and op_name == "+":
                t = str_concat_rule(o, r, e1, e2)
            elif isinstance(t1, ListType):
                if op_name != "+":
                    raise SemanticError(
                        f"Operator {op_name} cannot be applied on a list type")
                t = list_concat_rule(o, r, e1, e2)
            else:
                raise SemanticError(
                    f"Found {t1} but expected int, str, or list type")
        elif op_name in ["<", "<=", ">", ">=", "==", "!="]:
            t1 = check_expr(o, r, e1)
            if t1 == int_type:
                t = int_compare_rule(o, r, e1, op_name, e2)
            elif t1 == bool_type:
                if op_name not in ["==", "!="]:
                    raise SemanticError(
                        f"Operator {op_name} cannot be applied applied on a bool"
                    )
                t = bool_compare_rule(o, r, e1, op_name, e2)
            elif t1 == str_type:
                if op_name not in ["==", "!="]:
                    raise SemanticError(
                        f"Operator {op} cannot be applied applied on a str")
                t = str_compare_rule(o, r, e1, op_name, e2)
            else:
                raise SemanticError(
                    f"Found {t1} but expected int, bool, or str type")
        elif op_name == "and":
            t = and_rule(o, r, e1, e2)
        elif op_name == "or":
            t = or_rule(o, r, e1, e2)
        elif op_name == "is":
            t = is_rule(o, r, e1, e2)
        else:
            raise Exception(f"Unknown binary operation {op_name} found")
    elif isinstance(op, choco_ast.ExprName):
        t = var_read_rule(o, r, op.id.data)  #type: ignore
    elif isinstance(op, choco_ast.IfExpr):
        e0 = op.cond.op
        e1 = op.then.op
        e2 = op.or_else.op
        t = cond_rule(o, r, e1, e0, e2)
    elif isinstance(op, choco_ast.IndexExpr):
        e1 = op.value.op
        e2 = op.index.op
        t1 = check_expr(o, r, e1)
        if t1 == str_type:
            t = str_select_rule(o, r, e1, e2)
        elif isinstance(t1, ListType):
            t = list_select_rule(o, r, e1, e2)
        else:
            raise SemanticError(f"Found `{t1}' but expected str or list type")
    elif isinstance(op, choco_ast.ListExpr):
        es = op.elems.ops
        if len(es) >= 1:
            t = list_display_rule(o, r, es)
        else:
            t = nil_rule(o, r)
    elif isinstance(op, choco_ast.CallExpr):
        f = op.func.data  #type: ignore
        es = op.args.ops
        t = invoke_rule(o, r, f, es)

    assert isinstance(t, Type)

    op.attributes["type_hint"] = to_attribute(t)

    return t


# Typing rules, each typing rule is implemented by a corresponding function


# [VAR-READ] rule
# O, R |- id: T
def var_read_rule(o: LocalEnvironment, r: Type, id: str) -> Type:
    # O(id) = T, where T is not a function type.
    t = o.get(id)
    if t is None:
        raise SemanticError(f"Unknown identifier {id} used")
    if isinstance(t, FunctionInfo):
        raise SemanticError(
            f"Function identifier `{id}' used where value identifier expected")
    return t


# [VAR-INIT] rule
# O, R |- id: T = e1
def var_init_rule(o: LocalEnvironment, r: Type, id: str, e1: Operation):
    # O(id) = T
    t = o[id]
    if isinstance(t, FunctionInfo):
        raise SemanticError(
            f"Function identifier `{id}' used where value identifier expected")
    # O, R |- e1: T1
    t1 = check_expr(o, r, e1)
    # T1 ≤a T
    check_assignment_compatibility(t1, t)


# [STMT-DEF-LIST] rule
# O, R |- s1 NEWLINE s2 NEWLINE . . . sn NEWLINE
def stmt_def_list_rule(o: LocalEnvironment, r: Type, sns: List[Operation]):
    # n >= 1
    assert len(sns) >= 1
    for sn in sns:
        # O, R |- sn
        check_stmt_or_def(o, r, sn)


# [PASS] rule
# O, R |- pass
def pass_rule(o: LocalEnvironment, r: Type):
    pass


# [EXPR-STMT] rule
# O, R |- e
def expr_stmt_rule(o: LocalEnvironment, r: Type, e: Operation):
    # O, R |- e: T
    _t = check_expr(o, r, e)


# noinspection PySimplifyBooleanCheck
# O, R |- lit: T
def literal_rules(o: LocalEnvironment, r: Type,
                  lit: choco_ast.Literal) -> Type:
    if isinstance(lit.value, choco_ast.BoolAttr):
        # [BOOL-FALSE] rule
        if lit.value.data == False:
            return bool_type
        # [BOOL-TRUE] rule
        if lit.value.data == True:
            return bool_type
    # [NONE] rule
    if isinstance(lit.value, choco_ast.NoneAttr):
        return none_type
    # [INT] rule
    if isinstance(lit.value, choco_ast.IntegerAttr):
        return int_type
    # [STR] rule
    if isinstance(lit.value, choco_ast.StringAttr):
        return str_type
    raise Exception(f"Could not type check literal `{lit}'")


# [NEGATE] rule
# O, R, |- - e: int
def negate_rule(o: LocalEnvironment, r: Type, e: Operation) -> Type:
    # O, R, |- e: int
    check_type(check_expr(o, r, e), expected=int_type)
    return int_type


# [ARITH] rule
# O, R |- e1 op e2 : int
def arith_rule(o: LocalEnvironment, r: Type, e1: Operation, op: str,
               e2: Operation) -> Type:
    # op ∈ {+, −, ∗, //, %}
    assert op in ["+", "-", "*", "//", "%"]
    # O, R |- e1: int
    check_type(check_expr(o, r, e1), expected=int_type)
    # O, R |- e2: int
    check_type(check_expr(o, r, e2), expected=int_type)
    return int_type


# [INT-COMPARE] rule
# O, R |- e1 cmp_op e2 : bool
def int_compare_rule(o: LocalEnvironment, r: Type, e1: Operation, cmp_op: str,
                     e2: Operation) -> Type:
    # cmp_op ∈ {<,<=,>,>=,==,!=}
    assert cmp_op in ["<", "<=", ">", ">=", "==", "!="]
    # O, R |- e1: int
    check_type(check_expr(o, r, e1), expected=int_type)
    # O, R |- e2: int
    check_type(check_expr(o, r, e2), expected=int_type)
    return bool_type


# [BOOL-COMPARE] rule
# O, R |- e1 cmp_op e2 : bool
def bool_compare_rule(o: LocalEnvironment, r: Type, e1: Operation, cmp_op: str,
                      e2: Operation) -> Type:
    # cmp_op ∈ {==, !=}
    assert cmp_op in ["==", "!="]
    # O, R |- e1: bool
    check_type(check_expr(o, r, e1), expected=bool_type)
    # O, R |- e2: bool
    check_type(check_expr(o, r, e2), expected=bool_type)
    return bool_type


# [AND] rule
# O, R |- e1 and e2 : bool
def and_rule(o: LocalEnvironment, r: Type, e1: Operation,
             e2: Operation) -> Type:
    # O, R |- e1: bool
    check_type(check_expr(o, r, e1), expected=bool_type)
    # O, R |- e2: bool
    check_type(check_expr(o, r, e2), expected=bool_type)
    return bool_type


# [OR] rule
# O, R |- e1 or e2 : bool
def or_rule(o: LocalEnvironment, r: Type, e1: Operation,
            e2: Operation) -> Type:
    # O, R |- e1: bool
    check_type(check_expr(o, r, e1), expected=bool_type)
    # O, R |- e2: bool
    check_type(check_expr(o, r, e2), expected=bool_type)
    return bool_type


# [NOT] rule
# O, R |- not e : bool
def not_rule(o: LocalEnvironment, r: Type, e: Operation) -> Type:
    # O, R, |- e: bool
    check_type(check_expr(o, r, e), expected=bool_type)
    return bool_type


# [COND] rule
# O, R |- e1 if e0 else e2 : T1 |_| T2
def cond_rule(o: LocalEnvironment, r: Type, e1: Operation, e0: Operation,
              e2: Operation) -> Type:
    # O, R |- e0: bool
    check_type(check_expr(o, r, e0), expected=bool_type)
    # O, R |- e1: t1
    t1 = check_expr(o, r, e1)
    # O, R |- e2: t2
    t2 = check_expr(o, r, e2)

    return join(t1, t2)


# [STR-COMPARE] rule
# O, R |- e1 cmp_op e2 : bool
def str_compare_rule(o: LocalEnvironment, r: Type, e1: Operation, cmp_op: str,
                     e2: Operation) -> Type:
    # cmp_op ∈ {==, !=}
    assert cmp_op in ["==", "!="]
    # O, R |- e1: str
    check_type(check_expr(o, r, e1), expected=str_type)
    # O, R |- e2: str
    check_type(check_expr(o, r, e2), expected=str_type)
    return bool_type


# [STR-CONCAT]
# O, R |- e1 + e2 : str
def str_concat_rule(o: LocalEnvironment, r: Type, e1: Operation,
                    e2: Operation) -> Type:
    # O, R |- e1 : str
    check_type(check_expr(o, r, e1), expected=str_type)
    # O, R |- e2 : str
    check_type(check_expr(o, r, e2), expected=str_type)
    return str_type


# [STR-SELECT]
# O, R |- e1[e2] : str
def str_select_rule(o: LocalEnvironment, r: Type, e1: Operation,
                    e2: Operation) -> Type:
    # O, R |- e1 : str
    check_type(check_expr(o, r, e1), expected=str_type)
    # O, R |- e2 : int
    check_type(check_expr(o, r, e2), expected=int_type)
    return str_type


# [IS]
# O, R |- e1 is e2 : bool
def is_rule(o: LocalEnvironment, r: Type, e1: Operation,
            e2: Operation) -> Type:
    # O, R |- e1 : T1
    t1 = check_expr(o, r, e1)
    # O, R |- e1 : T2
    t2 = check_expr(o, r, e2)
    # T1, T2 are not one of int, str, bool
    if t1 in [int_type, str_type, bool_type]:
        raise SemanticError(
            f"Found `{t1}', expected type that is not int, str, or bool.")
    if t2 in [int_type, str_type, bool_type]:
        raise SemanticError(
            f"Found `{t1}', expected type that is not int, str, or bool.")

    return bool_type


# [LIST-DISPLAY]
# O, R |- [e1, e2, ..., en] : [T]
def list_display_rule(o: LocalEnvironment, r: Type,
                      es: List[Operation]) -> Type:
    # n >= 1
    assert len(es) >= 1
    # O, R |- ei : Ti
    ts = [check_expr(o, r, ei) for ei in es]
    # T = T1 |_| T2 |_| ... |_| Tn
    t = reduce(join, ts)

    return ListType(t)


# [NIL]
# O, R |- [] : <Empty>
def nil_rule(o: LocalEnvironment, r: Type) -> Type:
    return empty_type


# [LIST-CONCAT]
# O, R |- e1 + e2 : [T]
def list_concat_rule(o: LocalEnvironment, r: Type, e1: Operation,
                     e2: Operation) -> Type:
    # O, R |- e1 : [T1]
    t1 = check_list_type(check_expr(o, r, e1))
    # O, R |- e2 : [T2]
    t2 = check_list_type(check_expr(o, r, e2))
    # T = T1 |_| T2
    t = join(t1, t2)
    return ListType(t)


# [LIST-SELECT]
# O, R |- e1[e2] : T
def list_select_rule(o: LocalEnvironment, r: Type, e1: Operation,
                     e2: Operation) -> Type:
    # O, R |- e1 : [T]
    t = check_list_type(check_expr(o, r, e1))
    # O, R |- e2 : int
    check_type(check_expr(o, r, e2), expected=int_type)
    return t


# [LIST-ASSIGN-STMT] and [VAR-ASSIGN-STMT]
def assign_stmt_rule(o: LocalEnvironment, r: Type, target: Operation,
                     value: Operation):
    t1 = check_expr(o, r, target)
    t2 = check_expr(o, r, value)
    check_assignment_compatibility(t2, t1)


# [MULTI-ASSIGN-STMT]
# O,R |- e1 = e2 = ... = en = e0
def multi_assign_stmt(o: LocalEnvironment, r: Type, es: List[Operation],
                      e0: Operation):
    # n > 1
    assert len(es) > 1
    # O, R |- e0 : T0
    t0 = check_expr(o, r, e0)
    for ei in es:
        # O, R |- ei = e0
        assign_stmt_rule(o, r, ei, e0)
    # T0 != [<None>]
    if t0 == ListType(none_type):
        raise SemanticError(f"Type {t0} not allowed to be [<None>]")


# [INVOKE]
# O, R |- f(e1, e2, ..., en): T0
def invoke_rule(o: LocalEnvironment, r: Type, f: str,
                es: List[Operation]) -> Type:
    # O, R, |- ei : Ti''
    ts2 = [check_expr(o, r, ei) for ei in es]

    # O(f) = {T1 x ... x Tn -> T0; x1, ..., xn}
    function_info = o.get(f)
    if function_info is None:
        raise SemanticError(f"Unknown function {f}")
    if not isinstance(function_info, FunctionInfo):
        raise SemanticError(
            f"Value identifier `{id}' used where function identifier expected")

    if len(es) != len(function_info.func_type.inputs):
        raise SemanticError(
            f"Expected {len(function_info.func_type.inputs)} arguments, but got {len(es)}"
        )
    ts = function_info.func_type.inputs
    t0 = function_info.func_type.output

    # ∀ 1 ≤ i ≤ n : Ti′′ ≤a Ti
    for ti2, ti in zip(ts2, ts):
        check_assignment_compatibility(ti2, ti)

    return t0


# [RETURN-e] rule
# O, R |- return e
def return_e_rule(o: LocalEnvironment, r: Type, e: Operation):
    # O, R |- e : T
    t = check_expr(o, r, e)
    # T ≤a R
    check_assignment_compatibility(t, r)


# [RETURN] rule
# O, R |- return
def return_rule(o: LocalEnvironment, r: Type):
    # <None> ≤a R
    check_assignment_compatibility(none_type, r)


# [IF-ELSE]
# O, R |- if e: b1 else: b2
def if_else_rule(o: LocalEnvironment, r: Type, e: Operation,
                 b1: List[Operation], b2: Optional[List[Operation]]):
    # O, R |- e : bool
    check_type(check_expr(o, r, e), expected=bool_type)
    check_stmt_or_def_list(o, r, b1)
    if b2:
        check_stmt_or_def_list(o, r, b2)


# [WHILE]
# O, R |- while e: b
def while_rule(o: LocalEnvironment, r: Type, e: Operation, b: List[Operation]):
    # O, R |- e : bool
    check_type(check_expr(o, r, e), expected=bool_type)
    # O, R |- b
    check_stmt_or_def_list(o, r, b)


# [FOR-STR]
# O, R |- for id in e: b
def for_str_rule(o: LocalEnvironment, r: Type, id: str, e: Operation,
                 b: List[Operation]):
    # O, R |- e : str
    check_type(check_expr(o, r, e), expected=str_type)
    # O(id) = T
    t = o[id]
    if isinstance(t, FunctionInfo):
        raise SemanticError(
            f"Function identifier `{id}' used where value identifier expected")
    # str ≤a T
    check_assignment_compatibility(str_type, t)
    # O, R |- b
    check_stmt_or_def_list(o, r, b)


# [FOR-LIST]
# O, R |- for id in e: b
def for_list_rule(o: LocalEnvironment, r: Type, id: str, e: Operation,
                  b: List[Operation]):
    # O, R |- e : [T1]
    t1 = check_list_type(check_expr(o, r, e))
    # O(id) = T
    t = o[id]
    if isinstance(t, FunctionInfo):
        raise SemanticError(
            f"Function identifier `{id}' used where value identifier expected")
    # t1 ≤a T
    check_assignment_compatibility(t1, t)
    # O, R |- b
    check_stmt_or_def_list(o, r, b)


# [FUNC-DEF] rule
# O, R |- def f(x1:T1, ... , xn:Tn)  [[-> T0]]? :b
def func_def_rule(o: LocalEnvironment, r: Type, f: str, b: List[Operation]):
    # O(f) = {T1 x ... x Tn -> T; x1, ..., xn; v1: T1', ..., vm: Tm'}
    info = o[f]
    if isinstance(info, Type):
        raise SemanticError(
            f"Could not find function information for function {f} in context")
    ts = info.func_type.inputs
    t = info.func_type.output
    xs = info.params
    vs = info.nested_defs

    o = o.copy()
    for xi, ti in zip(xs, ts):
        o.update({xi: ti})
    for vi, ti in vs:
        o.update({vi: ti})
    # O[T1/x1]...[Tn/xn][T1'/v1]...[Tm'/vm] T |- b
    check_stmt_or_def_list(o, t, b)

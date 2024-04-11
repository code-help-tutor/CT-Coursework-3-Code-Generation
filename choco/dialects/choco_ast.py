WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Optional, Type, Union

from xdsl.utils.exceptions import ParseError

from choco.dialects import choco_type
from xdsl.dialects.builtin import IntegerAttr, StringAttr
from xdsl.ir import Data, MLContext, Operation, ParametrizedAttribute, Attribute, Dialect
from xdsl.irdl import (OpAttr, SingleBlockRegion, builder,
                       irdl_attr_definition, irdl_op_definition, OptOpAttr)
from xdsl.parser import BaseParser
from xdsl.printer import Printer


def get_type(annotation: str) -> Operation:
    return TypeName.get(annotation)


def get_statement_op_types() -> List[Type[Operation]]:
    statements: List[Type[Operation]] = [If, While, For, Pass, Return, Assign]
    return statements + get_expression_op_types()


def get_expression_op_types() -> List[Type[Operation]]:
    return [
        UnaryExpr, BinaryExpr, IfExpr, ExprName, ListExpr, IndexExpr, CallExpr,
        Literal
    ]


def get_type_op_types() -> List[Type[Operation]]:
    return [TypeName, ListType]


@irdl_op_definition
class Program(Operation):
    name = "choco.ast.program"

    # [VarDef | FuncDef]*
    defs: SingleBlockRegion

    # Stmt*
    stmts: SingleBlockRegion

    @staticmethod
    def get(defs: List[Operation],
            stmts: List[Operation],
            verify_op: bool = True) -> Program:
        res = Program.build(regions=[defs, stmts])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        for def_ in self.defs.blocks[0].ops:
            if type(def_) not in [VarDef, FuncDef]:
                raise Exception(
                    f"{Program.name} first region expects {VarDef.name} "
                    f"and {FuncDef.name} operations, but got {def_.name}")
        for stmt in self.stmts.blocks[0].ops:
            if type(stmt) not in get_statement_op_types():
                raise Exception(f"{Program.name} second region only expects "
                                f"statements operations, but got {stmt.name}")


@irdl_op_definition
class FuncDef(Operation):
    name = "choco.ast.func_def"

    func_name: OpAttr[StringAttr]
    params: SingleBlockRegion
    return_type: SingleBlockRegion

    # [GlobalDecl | NonLocalDecl | VarDef ]* Stmt+
    func_body: SingleBlockRegion

    @staticmethod
    def get(func_name: Union[str, StringAttr],
            params: List[Operation],
            return_type: Operation,
            func_body: List[Operation],
            verify_op: bool = True) -> FuncDef:
        res = FuncDef.build(attributes={"func_name": func_name},
                            regions=[params, [return_type], func_body])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        for param in self.params.blocks[0].ops:
            if not isinstance(param, TypedVar):
                raise Exception(
                    f"{FuncDef.name} first region expects {TypedVar.name} "
                    f"operations, but got {param.name}.")
        return_type = self.return_type.blocks[0].ops
        if len(return_type) != 1:
            raise Exception(f"{FuncDef.name} expects a single return type")
        if type(return_type[0]) not in get_type_op_types():
            raise Exception(
                f"{FuncDef.name} second region expects a single operation "
                f"representing a type, but got {return_type[0].name}.")
        stmt_region = False
        for stmt in self.func_body.blocks[0].ops:
            if not stmt_region:
                if type(stmt) in [GlobalDecl, NonLocalDecl, VarDef]:
                    continue
                else:
                    stmt_region = True
            if stmt_region:
                if not type(stmt) in get_statement_op_types():
                    raise Exception(
                        f"{FuncDef.name} third region expects variable declarations "
                        f"followed by statements, but got {stmt.name}")


@irdl_op_definition
class TypedVar(Operation):
    name = "choco.ast.typed_var"

    var_name: OpAttr[StringAttr]
    type: SingleBlockRegion

    @staticmethod
    def get(var_name: str,
            type: Operation,
            verify_op: bool = True) -> TypedVar:
        res = TypedVar.build(regions=[[type]],
                             attributes={"var_name": var_name})
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        typ = self.type.blocks[0].ops
        if len(typ) != 1 or type(typ[0]) not in get_type_op_types():
            raise Exception(
                f"{TypedVar.name} second region expects a single operation representing a type, but got {typ}."
            )


@irdl_op_definition
class TypeName(Operation):
    name = "choco.ast.type_name"

    type_name: OpAttr[StringAttr]

    @staticmethod
    def get(type_name: Union[str, StringAttr],
            verify_op: bool = True) -> TypeName:
        res = TypeName.build(attributes={"type_name": type_name})
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        legal_type_names = ["object", "int", "bool", "str", "<None>"]
        if self.type_name.data not in legal_type_names:  #type: ignore
            raise Exception(
                f"{self.name} expects type name, but got '{self.type_name.data}'"  #type: ignore
            )


@irdl_op_definition
class ListType(Operation):
    name = "choco.ast.list_type"

    elem_type: SingleBlockRegion

    @staticmethod
    def get(elem_type: Operation, verify_op: bool = True) -> ListType:
        res = ListType.build(regions=[[elem_type]])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        elem_type = self.elem_type.blocks[0].ops
        if len(elem_type) != 1 or type(
                elem_type[0]) not in get_type_op_types():
            raise Exception(
                f"{ListType.name} operation expects a single type operation in the first region."
            )


@irdl_op_definition
class GlobalDecl(Operation):
    name = "choco.ast.global_decl"

    decl_name: OpAttr[StringAttr]

    @staticmethod
    def get(decl_name: Union[str, StringAttr],
            verify_op: bool = True) -> GlobalDecl:
        res = GlobalDecl.build(attributes={"decl_name": decl_name})
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res


@irdl_op_definition
class NonLocalDecl(Operation):
    name = "choco.ast.nonlocal_decl"

    decl_name: OpAttr[StringAttr]

    @staticmethod
    def get(decl_name: Union[str, StringAttr],
            verify_op: bool = True) -> NonLocalDecl:
        res = NonLocalDecl.build(attributes={"decl_name": decl_name})
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res


@irdl_op_definition
class VarDef(Operation):
    name = "choco.ast.var_def"

    typed_var: SingleBlockRegion
    literal: SingleBlockRegion

    @staticmethod
    def get(typed_var: Operation,
            literal: Operation,
            verify_op: bool = True) -> VarDef:
        res = VarDef.build(regions=[[typed_var], [literal]])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        elem_type = self.typed_var.blocks[0].ops
        if len(elem_type) != 1 or not isinstance(elem_type[0], TypedVar):
            raise Exception(
                f"{VarDef.name} operation expects a single {TypedVar.name} operation in the first region."
            )
        literal = self.literal.blocks[0].ops
        if len(literal) != 1 or not isinstance(literal[0], Literal):
            raise Exception(
                f"{VarDef.name} operation expects a single {Literal.name} operation in the second region."
            )


# Statements


@irdl_op_definition
class If(Operation):
    name = "choco.ast.if"

    cond: SingleBlockRegion
    then: SingleBlockRegion
    orelse: SingleBlockRegion

    @staticmethod
    def get(cond: Operation,
            then: List[Operation],
            orelse: List[Operation],
            verify_op: bool = True) -> If:
        res = If.build(regions=[[cond], then, orelse])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        cond = self.cond.blocks[0].ops
        if len(cond) != 1 or type(cond[0]) not in get_expression_op_types():
            raise Exception(
                f"{If.name} operation expects a single expression in the first region."
            )
        for expr in self.then.blocks[0].ops:
            if type(expr) not in get_statement_op_types():
                raise Exception(
                    f"{If.name} operation expects statements operations in the second region."
                )
        for expr in self.orelse.blocks[0].ops:
            if type(expr) not in get_statement_op_types():
                raise Exception(
                    f"{If.name} operation expects statements operations in the third region."
                )


@irdl_op_definition
class While(Operation):
    name = "choco.ast.while"

    cond: SingleBlockRegion
    body: SingleBlockRegion

    @staticmethod
    def get(cond: Operation,
            body: List[Operation],
            verify_op: bool = True) -> While:
        res = While.build(regions=[[cond], body])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        cond = self.cond.blocks[0].ops
        if len(cond) != 1 or type(cond[0]) not in get_expression_op_types():
            raise Exception(
                f"{While.name} operation expects a single expression in the first region."
            )
        for stmt in self.body.blocks[0].ops:
            if type(stmt) not in get_statement_op_types():
                raise Exception(
                    f"{While.name} operation expects statements operations in the second region."
                )


@irdl_op_definition
class For(Operation):
    name = "choco.ast.for"

    iter_name: OpAttr[StringAttr]
    iter: SingleBlockRegion
    body: SingleBlockRegion

    @staticmethod
    def get(iter_name: Union[str, StringAttr],
            iter: Operation,
            body: List[Operation],
            verify_op: bool = True) -> For:
        res = For.build(attributes={"iter_name": iter_name},
                        regions=[[iter], body])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        iter = self.iter.blocks[0].ops
        if len(iter) != 1 or type(iter[0]) not in get_expression_op_types():
            raise Exception(
                f"{For.name} operation expects a single expression in the first region."
            )
        for stmt in self.body.blocks[0].ops:
            if type(stmt) not in get_statement_op_types():
                raise Exception(
                    f"{For.name} operation expects statements operations in the second region."
                )


@irdl_op_definition
class Pass(Operation):
    name = "choco.ast.pass"

    @staticmethod
    def get() -> Pass:
        return Pass.create()


@irdl_op_definition
class Return(Operation):
    name = "choco.ast.return"

    value: SingleBlockRegion

    @staticmethod
    def get(value: Optional[Operation], verify_op: bool = True) -> Return:
        res = Return.build(regions=[[value] if value is not None else []])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        value = self.value.blocks[0].ops
        if len(value) > 1 or (len(value) == 1 and type(value[0])
                              not in get_expression_op_types()):
            raise Exception(
                f"{Return.name} operation expects a single expression in the first region."
            )


@irdl_op_definition
class Assign(Operation):
    name = "choco.ast.assign"

    target: SingleBlockRegion
    value: SingleBlockRegion

    @staticmethod
    def get(target: Operation,
            value: Operation,
            verify_op: bool = True) -> Assign:
        res = Assign.build(regions=[[target], [value]])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        target = self.target.blocks[0].ops
        if len(target) != 1 or type(
                target[0]) not in get_expression_op_types():
            raise Exception(
                f"{Assign.name} operation expects a single expression in the first region, but get {target}."
            )
        for expr in self.value.blocks[0].ops:
            if type(expr) not in get_expression_op_types() + [Assign]:
                raise Exception(
                    f"{Assign.name} operation expects a single expression, or a single {Assign.name} operation in the second region."
                )


# Expressions


@irdl_attr_definition
class BoolAttr(Data[bool]):
    name = 'choco.ast.bool'

    @staticmethod
    def parse_parameter(parser: BaseParser) -> bool:
        val = parser.tokenizer.next_token_of_pattern(
            re.compile('(True|False)'))
        if val is None:
            parser.raise_error("Expected True or False literal")
            return True  # Not needed, but pyright complains
        return val.text == "True"

    @staticmethod
    def print_parameter(data: bool, printer: Printer) -> None:
        if data:
            printer.print_string("True")  # type: ignore
        else:
            printer.print_string("False")  # type: ignore

    @staticmethod
    @builder
    def from_bool(val: bool) -> BoolAttr:
        return BoolAttr(val)  # type: ignore


@irdl_attr_definition
class NoneAttr(ParametrizedAttribute):
    name = 'choco.ast.none'


@irdl_op_definition
class Literal(Operation):
    name = "choco.ast.literal"

    value: OpAttr[StringAttr | IntegerAttr | BoolAttr | NoneAttr]
    type_hint: OptOpAttr[Attribute]

    @staticmethod
    def get(value: Union[None, bool, int, str],
            verify_op: bool = True) -> Literal:
        if value is None:
            attr = NoneAttr()
        elif type(value) is bool:
            attr = BoolAttr.from_bool(value)
        elif type(value) is int:
            attr = IntegerAttr.from_int_and_width(value, 32)
        elif type(value) is str:
            attr = StringAttr.from_str(value)
        else:
            raise Exception(f"Unknown literal of type {type(value)}")
        res = Literal.create(attributes={"value": attr})
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res


@irdl_op_definition
class ExprName(Operation):
    name = "choco.ast.id_expr"

    id: OpAttr[StringAttr]
    type_hint: OptOpAttr[Attribute]

    @staticmethod
    def get(name: Union[str, StringAttr], verify_op: bool = True) -> ExprName:
        res = ExprName.build(attributes={"id": name})
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res


@irdl_op_definition
class UnaryExpr(Operation):
    name = "choco.ast.unary_expr"

    op: OpAttr[StringAttr]
    value: SingleBlockRegion

    type_hint: OptOpAttr[Attribute]

    @staticmethod
    def get_valid_ops() -> List[str]:
        return ["-", "not"]

    @staticmethod
    def get(op: Union[str, StringAttr],
            value: Operation,
            verify_op: bool = True) -> UnaryExpr:
        res = UnaryExpr.build(attributes={"op": op}, regions=[[value]])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        if self.op.data not in self.get_valid_ops():  #type: ignore
            raise Exception(
                f"Unsupported unary expression: '{self.op.data}'."  #type: ignore
            )
        value = self.value.blocks[0].ops
        if len(value) != 1 or type(value[0]) not in get_expression_op_types():
            raise Exception(
                f"{UnaryExpr.name} operation expects a single expression in the first region."
            )


@irdl_op_definition
class BinaryExpr(Operation):
    name = "choco.ast.binary_expr"

    op: OpAttr[StringAttr]
    lhs: SingleBlockRegion
    rhs: SingleBlockRegion

    type_hint: OptOpAttr[Attribute]

    @staticmethod
    def get_valid_ops() -> List[str]:
        return [
            "+", "-", "*", "//", "%", "and", "is", "or", ">", "<", "==", "!=",
            ">=", "<="
        ]

    @staticmethod
    def get(op: str,
            lhs: Operation,
            rhs: Operation,
            verify_op: bool = True) -> BinaryExpr:
        res = BinaryExpr.build(attributes={"op": op}, regions=[[lhs], [rhs]])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        if self.op.data not in self.get_valid_ops():  #type: ignore
            raise Exception(
                f"Unsupported unary expression: '{self.op.data}'."  #type: ignore
            )
        lhs = self.lhs.blocks[0].ops
        if len(lhs) != 1 or type(lhs[0]) not in get_expression_op_types():
            raise Exception(
                f"{BinaryExpr.name} operation expects a single expression in the first region."
            )
        rhs = self.rhs.blocks[0].ops
        if len(rhs) != 1 or type(rhs[0]) not in get_expression_op_types():
            raise Exception(
                f"{BinaryExpr.name} operation expects a single expression in the second region."
            )


@irdl_op_definition
class IfExpr(Operation):
    name = "choco.ast.if_expr"

    cond: SingleBlockRegion
    then: SingleBlockRegion
    or_else: SingleBlockRegion

    type_hint: OptOpAttr[Attribute]

    @staticmethod
    def get(cond: Operation,
            then: Operation,
            or_else: Operation,
            verify_op: bool = True) -> IfExpr:
        res = IfExpr.build(regions=[[cond], [then], [or_else]])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        cond = self.cond.blocks[0].ops
        if len(cond) != 1 or type(cond[0]) not in get_expression_op_types():
            raise Exception(
                f"{IfExpr.name} operation expects a single expression in the first region."
            )
        then = self.then.blocks[0].ops
        if len(then) != 1 or type(then[0]) not in get_expression_op_types():
            raise Exception(
                f"{IfExpr.name} operation expects a single expression in the second region."
            )
        or_else = self.or_else.blocks[0].ops
        if len(or_else) != 1 or type(
                or_else[0]) not in get_expression_op_types():
            raise Exception(
                f"{IfExpr.name} operation expects a single expression in the third region."
            )


@irdl_op_definition
class ListExpr(Operation):
    name = "choco.ast.list_expr"

    elems: SingleBlockRegion

    type_hint: OptOpAttr[Attribute]

    @staticmethod
    def get(elems: List[Operation], verify_op: bool = True) -> ListExpr:
        res = ListExpr.build(regions=[elems])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        for expr in self.elems.blocks[0].ops:
            if type(expr) not in get_expression_op_types():
                raise Exception(
                    f"{ListExpr.name} operation expects expression operations in the first region."
                )


@irdl_op_definition
class CallExpr(Operation):
    name = "choco.ast.call_expr"

    func: OpAttr[StringAttr]
    args: SingleBlockRegion
    type_hint: OptOpAttr[Attribute]

    @staticmethod
    def get(func: str,
            args: List[Operation],
            verify_op: bool = True) -> CallExpr:
        res = CallExpr.build(regions=[args], attributes={"func": func})
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        for arg in self.args.blocks[0].ops:
            if type(arg) not in get_expression_op_types():
                raise Exception(
                    f"{CallExpr.name} operation expects expression operations in the second region."
                )


@irdl_op_definition
class IndexExpr(Operation):
    name = "choco.ast.index_expr"

    value: SingleBlockRegion
    index: SingleBlockRegion

    type_hint: OptOpAttr[Attribute]

    @staticmethod
    def get(value: Operation,
            index: Operation,
            verify_op: bool = True) -> IndexExpr:
        res = IndexExpr.build(regions=[[value], [index]])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res

    def verify_(self) -> None:
        value = self.value.blocks[0].ops
        if len(value) != 1 or type(value[0]) not in get_expression_op_types():
            raise Exception(
                f"{IndexExpr.name} operation expects a single expression operation in the first region."
            )
        index = self.index.blocks[0].ops
        if len(index) != 1 or type(index[0]) not in get_expression_op_types():
            raise Exception(
                f"{IndexExpr.name} operation expects a single expression operation in the first region."
            )


ast_attrs: List[Type[Attribute]] = [
    choco_type.NamedType, choco_type.ListType, BoolAttr, NoneAttr
]

ast_ops: List[Type[Operation]] = [
    Program, FuncDef, TypedVar, TypeName, ListType, GlobalDecl, NonLocalDecl,
    VarDef, If, While, For, Pass, Return, Assign, Literal, ExprName, UnaryExpr,
    BinaryExpr, IfExpr, ListExpr, CallExpr, IndexExpr
]
ChocoAST = Dialect(ast_ops, ast_attrs)

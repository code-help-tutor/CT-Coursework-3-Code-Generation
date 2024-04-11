WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from __future__ import annotations
import re
from typing import Annotated, Union, List, Type
from io import StringIO

from dataclasses import dataclass
from xdsl.dialects.builtin import StringAttr, IntegerAttr
from xdsl.irdl import (irdl_op_definition, irdl_attr_definition, ParameterDef,
                       Operand, OptOpResult, SingleBlockRegion, OpAttr,
                       VarOperand, builder, OptOpAttr)
from xdsl.ir import (Dialect, ParametrizedAttribute, Operation, MLContext,
                     Data, SSAValue, Attribute, OpResult)

from xdsl.parser import BaseParser, Parser
from xdsl.printer import Printer

from choco.dialects import choco_type
from choco.dialects.choco_type import ListType, int_type, str_type, bool_type, none_type
from xdsl.utils.diagnostic import Diagnostic


def error(op: Operation, msg: str):
    diag = Diagnostic()
    diag.add_message(op, msg)
    diag.raise_exception(f"{op.name} operation does not verify", op)


@irdl_attr_definition
class BoolAttr(Data[bool]):
    name = 'choco.ir.bool'

    @staticmethod
    def parse_parameter(parser: BaseParser) -> bool:
        val = parser.tokenizer.next_token_of_pattern(
            re.compile('(True|False)'))
        if val is None:
            parser.raise_error("Expected True or False literal")
            return True  # Not needed, but pyright complains
        return val.text == "True"

    @staticmethod
    def print_parameter(val: bool, printer: Printer) -> None:
        if val:
            printer.print_string("True")  # type: ignore
        else:
            printer.print_string("False")  # type: ignore

    @staticmethod
    @builder
    def from_bool(val: bool) -> BoolAttr:
        return BoolAttr(val)  # type: ignore


@irdl_attr_definition
class NoneAttr(ParametrizedAttribute):
    name = 'choco.ir.none'


@irdl_op_definition
class ClassDef(Operation):
    name = "choco.ir.class_def"

    class_name: OpAttr[StringAttr]
    super_class_name: OpAttr[StringAttr]
    class_body: SingleBlockRegion


@irdl_op_definition
class FuncDef(Operation):
    name = "choco.ir.func_def"

    func_name: OpAttr[StringAttr]
    return_type: OpAttr[Attribute]
    func_body: SingleBlockRegion


# Statements


@irdl_op_definition
class If(Operation):
    name = "choco.ir.if"

    cond: Annotated[Operand, choco_type.bool_type]
    then: SingleBlockRegion
    orelse: SingleBlockRegion


@irdl_op_definition
class While(Operation):
    name = "choco.ir.while"

    cond: SingleBlockRegion
    body: SingleBlockRegion

    @property
    def cond_ssa_value(self) -> SSAValue:
        yield_ = self.cond.ops[-1]
        assert isinstance(yield_, Yield)
        return yield_.value  # type: ignore

    def verify_(self) -> None:
        yield_ = self.cond.ops[-1]
        if not isinstance(yield_, Yield):
            raise Exception(
                f"{While.name} operation expects last operation in condition to be a {Yield.name}"
            )
        if not (yield_.value.typ == bool_type):  # type: ignore
            raise Exception(
                f"{While.name} operation expects last operation in condition to have type {bool_type.name}"
            )


@irdl_op_definition
class For(Operation):
    name = "choco.ir.for"

    iter_: Annotated[Operand, Attribute]
    target: Annotated[Operand, Attribute]
    body: SingleBlockRegion


@irdl_op_definition
class Pass(Operation):
    name = "choco.ir.pass"


@irdl_op_definition
class Return(Operation):
    name = "choco.ir.return"

    value: Annotated[Operand, Attribute]


@irdl_op_definition
class Yield(Operation):
    name = "choco.ir.yield"

    value: Annotated[Operand, Attribute]

    @staticmethod
    def get(value: Union[SSAValue, Operation]) -> Yield:
        return Yield.build(operands=[value])


@irdl_op_definition
class Assign(Operation):
    name = "choco.ir.assign"

    target: Annotated[Operand, Attribute]
    value: Annotated[Operand, Attribute]

    def verify_(self) -> None:
        from riscv.ssa_dialect import RegisterType
        if isinstance(
                self.target.typ,  # type: ignore
                RegisterType) or isinstance(
                    self.value.typ,  # type: ignore
                    RegisterType):
            # TODO: I don't know what to do here, so I pass
            pass
        else:
            from choco.type_checking import Type, check_assignment_compatibility
            target_type = Type.from_attribute(self.target.typ)  # type: ignore
            value_type = Type.from_attribute(self.value.typ)  # type: ignore
            check_assignment_compatibility(value_type, target_type)


# Expressions


@irdl_op_definition
class Literal(Operation):
    name = "choco.ir.literal"

    value: OpAttr[Attribute]
    result: OpResult

    @staticmethod
    def get(value: Union[None, bool, int, str],
            verify_op: bool = True) -> Literal:
        if value is None:
            attr = NoneAttr()
            ty = none_type
        elif type(value) is bool:
            attr = BoolAttr.from_bool(value)
            ty = bool_type
        elif type(value) is int:
            attr = IntegerAttr.from_int_and_width(value, 32)
            ty = int_type
        elif type(value) is str:
            attr = StringAttr.from_str(value)
            ty = str_type
        else:
            raise Exception(f"Unknown literal of type {type(value)}")

        res = Literal.build(operands=[],
                            attributes={"value": attr},
                            result_types=[ty])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            res.verify(verify_nested_ops=False)
        return res


@irdl_op_definition
class UnaryExpr(Operation):
    name = "choco.ir.unary_expr"

    op: OpAttr[StringAttr]
    value: Annotated[Operand, Attribute]
    result: OpResult


@irdl_op_definition
class BinaryExpr(Operation):
    name = "choco.ir.binary_expr"

    op: OpAttr[StringAttr]
    lhs: Annotated[Operand, Attribute]
    rhs: Annotated[Operand, Attribute]
    result: OpResult


@irdl_op_definition
class EffectfulBinaryExpr(Operation):
    name = "choco.ir.effectful_binary_expr"

    op: OpAttr[StringAttr]
    lhs: SingleBlockRegion
    rhs: SingleBlockRegion
    result: OpResult


@irdl_op_definition
class IfExpr(Operation):
    name = "choco.ir.if_expr"

    cond: Annotated[Operand, choco_type.bool_type]
    then: SingleBlockRegion
    or_else: SingleBlockRegion
    result: OpResult

    @property
    def then_ssa_value(self) -> SSAValue:
        then_ = self.then.ops[-1]
        assert isinstance(then_, Yield)
        return then_.value  # type: ignore

    @property
    def or_else_ssa_value(self) -> SSAValue:
        or_else_ = self.or_else.ops[-1]
        assert isinstance(or_else_, Yield)
        return or_else_.value  # type: ignore

    def verif_(self) -> None:
        then_ = self.then.ops
        if not isinstance(then_[-1], Yield):
            raise Exception(
                f"{IfExpr.name} operation expects last operation in then branch to be a {Yield.name}"
            )
        or_else_ = self.or_else.ops
        if not isinstance(or_else_[-1], Yield):
            raise Exception(
                f"{IfExpr.name} operation expects last operation in or else branch to be a {Yield.name}"
            )


@irdl_op_definition
class ListExpr(Operation):
    name = "choco.ir.list_expr"

    elems: VarOperand
    result: OpResult


@irdl_op_definition
class CallExpr(Operation):
    name = "choco.ir.call_expr"

    args: VarOperand
    func_name: OpAttr[Attribute]
    result: OptOpResult

    type_hint: OptOpAttr[Attribute]


@irdl_op_definition
class MemberExpr(Operation):
    name = "choco.ir.member_expr"

    value: Annotated[Operand, Attribute]
    attribute: OpAttr[StringAttr]
    result: OpResult


# Memory operations


@irdl_attr_definition
class MemlocType(ParametrizedAttribute):
    name = "choco.ir.memloc"

    type: ParameterDef[choco_type.NamedType | choco_type.ListType]


@irdl_op_definition
class Alloc(Operation):
    name = "choco.ir.alloc"

    type: OpAttr[choco_type.NamedType | choco_type.ListType]
    memloc: Annotated[OpResult, MemlocType]

    def verify_(self) -> None:
        if self.type != self.memloc.typ.type:  # type: ignore
            error(self, "expected types to match")


@irdl_op_definition
class IndexString(Operation):
    name = "choco.ir.index_string"

    value: Annotated[Operand, Attribute]
    index: Annotated[Operand, choco_type.int_type]
    result: Annotated[OpResult, MemlocType]

    def verify_(self) -> None:
        if isinstance(self.value.typ, ListType):  # type: ignore
            if self.value.typ.elem_type != self.result.typ.type:  # type: ignore
                error(self, "expected types to match")
        elif self.value.typ == choco_type.str_type:  # type: ignore
            if self.result.typ.type != choco_type.str_type:  # type: ignore
                error(self, "expected types to match")
        else:
            error(self, "expected List of String type")


@irdl_op_definition
class GetAddress(Operation):
    name = "choco.ir.get_address"

    value: Annotated[Operand, Attribute]
    index: Annotated[Operand, choco_type.int_type]
    result: Annotated[OpResult, MemlocType]

    def verify_(self) -> None:
        if isinstance(self.value.typ, ListType):  # type: ignore
            if self.value.typ.elem_type != self.result.typ.type:  # type: ignore
                error(self, "expected types to match")
        elif self.value.typ == choco_type.str_type:  # type: ignore
            if self.result.typ.type != choco_type.str_type:  # type: ignore
                error(self, "expected types to match")
        else:
            error(self, "expected List of String type")


@irdl_op_definition
class Load(Operation):
    name = "choco.ir.load"

    memloc: Annotated[Operand, MemlocType]
    result: OpResult

    def verify_(self) -> None:
        if self.result.typ != self.memloc.typ.type:  # type: ignore
            sio = StringIO()
            p = Printer(stream=sio)
            p.print_attribute(self.result.typ)  # type: ignore
            type_str = sio.getvalue()

            error(
                self,
                f"Mismatched operand types! Should the first operand be of type !choco.ir.memloc<{type_str}>?"
            )


@irdl_op_definition
class Store(Operation):
    name = "choco.ir.store"

    memloc: Annotated[Operand, MemlocType]
    value: Annotated[Operand, Attribute]

    def verify_(self) -> None:
        if self.value.typ != self.memloc.typ.type:  # type: ignore
            if (isinstance(  # type: ignore
                    self.memloc.typ.type,  # type: ignore
                    choco_type.ListType)):  # type: ignore
                if (self.value.typ  # type: ignore
                        in [  # type: ignore
                            choco_type.empty_type,  # type: ignore
                            choco_type.none_type  # type: ignore
                        ]):  # type: ignore
                    return
            if self.memloc.typ.type == choco_type.object_type:  # type: ignore
                return
            sio = StringIO()
            p = Printer(stream=sio)
            p.print_attribute(self.value.typ)  # type: ignore
            type_str = sio.getvalue()

            error(
                self,
                f"Mismatched operand types! Should the first operand be of type !choco.ir.memloc<{type_str}>?"
            )


choco_flat_attrs: List[Type[Attribute]] = [NoneAttr, BoolAttr, MemlocType]
choco_flat_ops: List[Type[Operation]] = [
    ClassDef,
    FuncDef,
    If,
    While,
    For,
    Pass,
    Return,
    Assign,
    Literal,
    UnaryExpr,
    BinaryExpr,
    EffectfulBinaryExpr,
    IfExpr,
    ListExpr,
    CallExpr,
    MemberExpr,
    Alloc,
    GetAddress,
    IndexString,
    Load,
    Store,
    Yield,
]

ChocoFlat = Dialect(choco_flat_ops, choco_flat_attrs)

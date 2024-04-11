WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from __future__ import annotations

import riscv.dialect

from xdsl.ir import (Operation, ParametrizedAttribute, SSAValue, Dialect,
                     Attribute, OpResult)
from xdsl.irdl import (irdl_op_definition, irdl_attr_definition, OptOpResult,
                       Operand, VarOperand, SingleBlockRegion, OptOperand,
                       OpAttr, OptOpAttr)
from xdsl.dialects.builtin import AnyIntegerAttr, StringAttr, IntegerAttr

from typing import Annotated, Type, Dict, Union, Optional, Any, List


@irdl_attr_definition
class RegisterType(ParametrizedAttribute):
    name = "riscv_ssa.reg"


class Riscv1Rd1Rs1ImmOperation(Operation):
    rd: Annotated[OpResult, RegisterType]
    rs1: Annotated[Operand, RegisterType]
    immediate: OpAttr[AnyIntegerAttr]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            rs1: Union[Operation, SSAValue],
            immediate: Union[int, IntegerAttr],
            comment: Optional[str] = None) -> riscv.dialect.Op:
        if isinstance(immediate, int):
            immediate = IntegerAttr.from_int_and_width(immediate, 32)

        attributes: Dict[str, Any] = {
            "immediate": immediate,
        }
        if comment:
            attributes["comment"] = comment
        return cls.build(operands=[rs1],
                         result_types=[RegisterType()],
                         attributes=attributes)


class Riscv2Rs1ImmOperation(Operation):
    rs1: Annotated[Operand, RegisterType]
    rs2: Annotated[Operand, RegisterType]
    immediate: OpAttr[AnyIntegerAttr]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            rs1: Union[Operation, SSAValue],
            rs2: Union[Operation, SSAValue],
            immediate: Union[int, AnyIntegerAttr],
            comment: Optional[str] = None) -> riscv.dialect.Op:
        if isinstance(immediate, int):
            immediate = IntegerAttr.from_int_and_width(immediate, 32)

        attributes: Dict[str, Any] = {
            "immediate": immediate,
        }
        if comment:
            attributes["comment"] = comment
        return cls.build(operands=[rs1, rs2], attributes=attributes)


class Riscv2Rs1OffOperation(Operation):
    rs1: Annotated[Operand, RegisterType]
    rs2: Annotated[Operand, RegisterType]
    offset: OpAttr[AnyIntegerAttr | riscv.dialect.LabelAttr]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            rs1: Union[Operation, SSAValue],
            rs2: Union[Operation, SSAValue],
            offset: Union[int, AnyIntegerAttr, riscv.dialect.LabelAttr],
            comment: Optional[str] = None) -> riscv.dialect.Op:
        if isinstance(offset, int):
            offset = IntegerAttr.from_int_and_width(offset, 32)
        if isinstance(offset, str):
            offset = riscv.dialect.LabelAttr.from_str(offset)

        attributes: Dict[str, Any] = {
            "offset": offset,
        }
        if comment:
            attributes["comment"] = comment
        return cls.build(operands=[rs1, rs2], attributes=attributes)


class Riscv1Rd2RsOperation(Operation):
    rd: Annotated[OpResult, RegisterType]
    rs1: Annotated[Operand, RegisterType]
    rs2: Annotated[Operand, RegisterType]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            rs1: Union[Operation, SSAValue],
            rs2: Union[Operation, SSAValue],
            comment: Optional[str] = None) -> riscv.dialect.Op:

        attributes: Dict[str, Any] = {}
        if comment:
            attributes["comment"] = comment
        return cls.build(operands=[rs1, rs2],
                         attributes=attributes,
                         result_types=[RegisterType()])


class Riscv1Rs1Rt1OffOperation(Operation):
    rs: Annotated[OpResult, RegisterType]
    rt: Annotated[Operand, RegisterType]
    offset: OpAttr[AnyIntegerAttr]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            rt: Union[Operation, SSAValue],
            offset: Union[int, AnyIntegerAttr],
            comment: Optional[str] = None) -> riscv.dialect.Op:
        if isinstance(offset, int):
            offset = IntegerAttr.from_int_and_width(offset, 32)

        attributes: Dict[str, Any] = {
            "offset": offset,
        }
        if comment:
            attributes["comment"] = comment
        return cls.build(operands=[rt], attributes=attributes)


class Riscv1OffOperation(Operation):
    offset: OpAttr[AnyIntegerAttr | riscv.dialect.LabelAttr]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            offset: Union[int, AnyIntegerAttr, riscv.dialect.LabelAttr],
            comment: Optional[str] = None) -> riscv.dialect.Op:
        if isinstance(offset, int):
            offset = IntegerAttr.from_int_and_width(offset, 32)
        if isinstance(offset, str):
            offset = riscv.dialect.LabelAttr.from_str(offset)

        attributes: Dict[str, Any] = {
            "offset": offset,
        }
        if comment:
            attributes["comment"] = comment
        return cls.build(attributes=attributes)


class Riscv1Rd1ImmOperation(Operation):
    rd: Annotated[OpResult, RegisterType]
    immediate: OpAttr[AnyIntegerAttr | riscv.dialect.LabelAttr]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            immediate: Union[int, AnyIntegerAttr],
            comment: Optional[str] = None) -> riscv.dialect.Op:
        if isinstance(immediate, int):
            immediate = IntegerAttr.from_int_and_width(immediate, 32)

        attributes: Dict[str, Any] = {
            "immediate": immediate,
        }
        if comment:
            attributes["comment"] = comment
        return cls.build(result_types=[RegisterType()], attributes=attributes)


class Riscv1Rd1OffOperation(Operation):
    rd: Annotated[OpResult, RegisterType]
    offset: OpAttr[AnyIntegerAttr]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            offset: Union[int, AnyIntegerAttr],
            comment: Optional[str] = None) -> riscv.dialect.Op:
        if isinstance(offset, int):
            offset = IntegerAttr.from_int_and_width(offset, 32)

        attributes: Dict[str, Any] = {
            "offset": offset,
        }
        if comment:
            attributes["comment"] = comment
        return cls.build(attributes=attributes, result_types=[RegisterType()])


class Riscv1Rs1OffOperation(Operation):
    rs: Annotated[Operand, RegisterType]
    offset: OpAttr[AnyIntegerAttr]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            rs: Union[Operation, SSAValue],
            offset: Union[int, AnyIntegerAttr],
            comment: Optional[str] = None) -> riscv.dialect.Op:
        if isinstance(offset, int):
            offset = IntegerAttr.from_int_and_width(offset, 32)

        attributes: Dict[str, Any] = {
            "offset": offset,
        }
        if comment:
            attributes["comment"] = comment
        return cls.build(operands=[rs], attributes=attributes)


class Riscv1Rd1RsOperation(Operation):
    rd: Annotated[OpResult, RegisterType]
    rs: Annotated[Operand, RegisterType]
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            rs: Union[Operation, SSAValue],
            comment: Optional[str] = None) -> riscv.dialect.Op:

        attributes: Dict[str, Any] = {}
        if comment:
            attributes["comment"] = comment
        return cls.build(operands=[rs],
                         result_types=[RegisterType()],
                         attributes=attributes)


class RiscvNoParamsOperation(Operation):
    comment: OptOpAttr[StringAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            comment: Optional[str] = None) -> riscv.dialect.Op:

        attributes: Dict[str, Any] = {}
        if comment:
            attributes["comment"] = comment
        return cls.build(attributes=attributes)


@irdl_op_definition
class LBOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.lb"


@irdl_op_definition
class LBUOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.lbu"


@irdl_op_definition
class LHOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.lh"


@irdl_op_definition
class LHUOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.lhu"


@irdl_op_definition
class LWOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.lw"


# Stores


@irdl_op_definition
class SBOp(Riscv2Rs1ImmOperation):
    name = "riscv_ssa.sb"


@irdl_op_definition
class SHOp(Riscv2Rs1ImmOperation):
    name = "riscv_ssa.sh"


@irdl_op_definition
class SWOp(Riscv2Rs1ImmOperation):
    name = "riscv_ssa.sw"


# Branches


@irdl_op_definition
class BEQOp(Riscv2Rs1OffOperation):
    name = "riscv_ssa.beq"


@irdl_op_definition
class BNEOp(Riscv2Rs1OffOperation):
    name = "riscv_ssa.bne"


@irdl_op_definition
class BLTOp(Riscv2Rs1OffOperation):
    name = "riscv_ssa.blt"


@irdl_op_definition
class BGEOp(Riscv2Rs1OffOperation):
    name = "riscv_ssa.bge"


@irdl_op_definition
class BLTUOp(Riscv2Rs1OffOperation):
    name = "riscv_ssa.bltu"


@irdl_op_definition
class BGEUOp(Riscv2Rs1OffOperation):
    name = "riscv_ssa.bgeu"


# Shifts


@irdl_op_definition
class SLLOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.sll"


@irdl_op_definition
class SLLIOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.slli"


@irdl_op_definition
class SRLOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.srl"


@irdl_op_definition
class SRLIOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.srli"


@irdl_op_definition
class SRAOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.sra"


@irdl_op_definition
class SRAIOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.srai"


# Arithmetic


@irdl_op_definition
class AddOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.add"


@irdl_op_definition
class AddIOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.addi"


@irdl_op_definition
class SubOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.sub"


@irdl_op_definition
class LUIOp(Riscv1Rd1ImmOperation):
    name = "riscv_ssa.lui"


@irdl_op_definition
class LIOp(Riscv1Rd1ImmOperation):
    name = "riscv_ssa.li"


@irdl_op_definition
class AUIPCOp(Riscv1Rd1ImmOperation):
    name = "riscv_ssa.auipc"


# Logical


@irdl_op_definition
class XOROp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.xor"


@irdl_op_definition
class XORIOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.xori"


@irdl_op_definition
class OROp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.or"


@irdl_op_definition
class ORIOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.ori"


@irdl_op_definition
class ANDOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.and"


@irdl_op_definition
class ANDIOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.andi"


# Compare


@irdl_op_definition
class SLTOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.slt"


@irdl_op_definition
class SLTIOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.slti"


@irdl_op_definition
class SLTUOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.sltu"


@irdl_op_definition
class SLTIUOp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.sltiu"


# Jump & Link


@irdl_op_definition
class JOp(Riscv1OffOperation):
    name = "riscv_ssa.j"


@irdl_op_definition
class JALOp(Riscv1Rd1ImmOperation):
    name = "riscv_ssa.jal"


@irdl_op_definition
class JALROp(Riscv1Rd1Rs1ImmOperation):
    name = "riscv_ssa.jalr"


# System


@irdl_op_definition
class ECALLOp(Operation):
    name = "riscv_ssa.ecall"
    syscall_num: Annotated[Operand, RegisterType]
    args: Annotated[VarOperand, RegisterType]


@irdl_op_definition
class EBREAKOp(Operation):
    name = "riscv_ssa.ebreak"


#  Optional Multiply-Divide Instruction Extension (RVM)


@irdl_op_definition
class MULOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.mul"


@irdl_op_definition
class MULHOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.mulh"


@irdl_op_definition
class MULHSUOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.mulhsu"


@irdl_op_definition
class MULHUOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.mulhu"


@irdl_op_definition
class DIVOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.div"


@irdl_op_definition
class DIVUOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.divu"


@irdl_op_definition
class REMOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.rem"


@irdl_op_definition
class REMUOp(Riscv1Rd2RsOperation):
    name = "riscv_ssa.remu"


@irdl_op_definition
class CallOp(Operation):
    name = "riscv_ssa.call"
    args: Annotated[VarOperand, RegisterType]
    func_name: OpAttr[StringAttr]
    result: Annotated[OptOpResult, RegisterType]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            func_name: Union[str, StringAttr],
            args: List[Union[Operation, SSAValue]],
            has_result: bool = True,
            comment: Optional[Union[str,
                                    StringAttr]] = None) -> riscv.dialect.Op:
        attributes: Dict[str, Any] = {"func_name": func_name}
        if comment is not None:
            attributes["comment"] = StringAttr.build(comment)
        return cls.build(
            operands=[args],
            result_types=[[RegisterType()]] if has_result else [[]],
            attributes=attributes)


@irdl_op_definition
class LabelOp(Operation):
    name = "riscv_ssa.label"
    label: OpAttr[riscv.dialect.LabelAttr]

    @classmethod
    def get(cls: Type[riscv.dialect.Op],
            label: Union[str, StringAttr],
            comment: Optional[str] = None) -> riscv.dialect.Op:
        attributes: Dict[str, Any] = {
            "label": label,
        }
        if comment:
            attributes["comment"] = comment
        return cls.build(operands=[], result_types=[], attributes=attributes)


@irdl_op_definition
class DirectiveOp(Operation):
    name = "riscv_ssa.directive"
    directive: OpAttr[StringAttr]
    value: OpAttr[StringAttr]


@irdl_op_definition
class AllocOp(Operation):
    name = "riscv_ssa.alloc"
    rd: Annotated[OpResult, RegisterType]

    @classmethod
    def get(cls: Type[riscv.dialect.Op]) -> riscv.dialect.Op:
        return cls.build(result_types=[RegisterType()])


@irdl_op_definition
class FuncOp(Operation):
    name = "riscv_ssa.func"

    func_name: OpAttr[StringAttr]
    func_body: SingleBlockRegion


@irdl_op_definition
class ReturnOp(Operation):
    name = "riscv_ssa.return"
    value: Annotated[OptOperand, RegisterType]

    @classmethod
    def get(
        cls: Type[riscv.dialect.Op],
        value: Optional[Union[Operation,
                              SSAValue]] = None) -> riscv.dialect.Op:
        operands: List[Operation | SSAValue] = []

        if value != None:
            operands.append(value)

        return cls.build(operands=operands)


riscv_ssa_attrs: List[Type[Attribute]] = [RegisterType]
riscv_ssa_ops: List[Type[Operation]] = [
    LBOp, LBUOp, LHOp, LHUOp, LWOp, SBOp, SHOp, SWOp, BEQOp, BNEOp, BLTOp,
    BGEOp, BLTUOp, BGEUOp, AddOp, AddIOp, SubOp, LUIOp, LIOp, AUIPCOp, XOROp,
    XORIOp, OROp, ORIOp, ANDOp, ANDIOp, SLTOp, SLTIOp, SLTUOp, SLTIUOp, JOp,
    JALOp, JALROp, ECALLOp, EBREAKOp, MULOp, MULHOp, MULHSUOp, MULHUOp, DIVOp,
    DIVUOp, REMOp, REMUOp, LabelOp, CallOp, AllocOp, FuncOp, ReturnOp
]
RISCVSSA = Dialect(riscv_ssa_ops, riscv_ssa_attrs)

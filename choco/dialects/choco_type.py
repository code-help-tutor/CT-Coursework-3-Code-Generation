WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import ParametrizedAttribute, Attribute
from xdsl.irdl import ParameterDef, irdl_attr_definition


@irdl_attr_definition
class NamedType(ParametrizedAttribute):
    name = "choco.ir.named_type"

    type_name: ParameterDef[StringAttr]


@irdl_attr_definition
class ListType(ParametrizedAttribute):
    name = "choco.ir.list_type"

    elem_type: ParameterDef[Attribute]


int_type = NamedType([StringAttr.from_str("int")])
bool_type = NamedType([StringAttr.from_str("bool")])
str_type = NamedType([StringAttr.from_str("str")])
none_type = NamedType([StringAttr.from_str("<None>")])
empty_type = NamedType([StringAttr.from_str("<Empty>")])
object_type = NamedType([StringAttr.from_str("object")])

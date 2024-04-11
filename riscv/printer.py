WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from riscv.dialect import *
import sys


def print_op(op, stream=sys.stdout):
    attr = op.attributes

    if isinstance(op, CommentOp):
        if 'comment' in attr.keys():
            print(f"    \t# {attr['comment'].data}", file=stream)
        else:
            print("", file=stream)

        return

    if isinstance(op, LabelOp):
        print("%s:" % (attr['label'].data), file=stream)
        return

    if isinstance(op, DirectiveOp):
        print(".%s %s" % (attr['directive'].data, attr['value'].data),
              file=stream)
        return

    name = op.name[6:]

    print(f"\t{name}", end='', file=stream)

    if isinstance(op, RiscvNoParamsOperation):
        print("", file=stream, end="")

    elif isinstance(op, Riscv1Rd1ImmOperation):
        print(" %s, %s" %
              (attr['rd'].data.get_abi_name(), attr['immediate'].value.data),
              file=stream,
              end="")

    elif isinstance(op, Riscv1OffOperation):
        if isinstance(attr['offset'], IntegerAttr):
            offset = attr['offset'].parameters[0].data
        else:
            offset = attr['offset'].data
        print(" %s" % (offset), file=stream, end="")

    elif isinstance(op, Riscv1Rd1OffOperation):
        if isinstance(attr['offset'], IntegerAttr):
            offset = attr['offset'].parameters[0].data
        else:
            offset = attr['offset'].data
        print(" %s, %s" % (attr['rd'].data.get_abi_name(), offset),
              file=stream,
              end="")

    elif isinstance(op, Riscv1Rd1RsOperation):
        print(" %s, %s" %
              (attr['rd'].data.get_abi_name(), attr['rs'].data.get_abi_name()),
              file=stream,
              end="")

    elif isinstance(op, Riscv1Rs1OffOperation):
        if isinstance(attr['offset'], IntegerAttr):
            offset = attr['offset'].parameters[0].data
        else:
            offset = attr['offset'].data
        print(" %s, %s" % (attr['rs'].data.get_abi_name(), offset),
              file=stream,
              end="")

    elif isinstance(op, Riscv1Rd2RsOperation):
        print(" %s, %s, %s" %
              (attr['rd'].data.get_abi_name(), attr['rs1'].data.get_abi_name(),
               attr['rs2'].data.get_abi_name()),
              file=stream,
              end="")

    elif isinstance(op, Riscv1Rd1Rs1ImmOperation):
        rd = attr['rd'].data.get_abi_name()
        rs1 = attr['rs1'].data.get_abi_name()
        immediate = attr['immediate'].value.data
        if isinstance(op, (LBOp, LBUOp, LHOp, LHUOp, LWOp)):
            output = f" {rd}, {immediate}({rs1})"
        else:
            output = f" {rd}, {rs1}, {immediate}"
        print(output, file=stream, end="")

    elif isinstance(op, Riscv1Rd1RsOperation):
        print(
            " %s, %s" %
            (attr['rd'].data.get_abi_name(), attr['rs1'].data.get_abi_name()),
            end='',
            file=stream)

        immediate = attr['immediate'].value.data
        print(", %s" % (immediate), file=stream, end="")

    elif isinstance(op, Riscv2Rs1ImmOperation):
        rs1 = attr['rs1'].data.get_abi_name()
        rs2 = attr['rs2'].data.get_abi_name()
        immediate = attr['immediate'].value.data
        if isinstance(op, (SBOp, SHOp, SWOp)):
            output = f" {rs1}, {immediate}({rs2})"
        else:
            output = f" {rs1}, {rs2}, {immediate}"
        print(output, file=stream, end="")

    elif isinstance(op, Riscv2Rs1OffOperation):
        if isinstance(attr['offset'], IntegerAttr):
            offset = attr['offset'].parameters[0].data
        else:
            offset = attr['offset'].data

        print(" %s, %s, %s" % (attr['rs1'].data.get_abi_name(),
                               attr['rs2'].data.get_abi_name(), offset),
              file=stream,
              end="")

    elif isinstance(op, Riscv1Rs1Rt1OffOperation):
        if isinstance(attr['offset'], IntegerAttr):
            offset = attr['offset'].parameters[0].data
        else:
            offset = attr['offset'].data

        print(" %s, %s, %s" % (attr['rs'].data.get_abi_name(),
                               attr['rt'].data.get_abi_name(), offset),
              file=stream,
              end="")

    elif isinstance(op, Riscv1Rd1Rs1OffOperation):
        if isinstance(attr['offset'], IntegerAttr):
            offset = attr['offset'].parameters[0].data
        else:
            offset = attr['offset'].data

        print(" %s, %s, %s" % (attr['rd'].data.get_abi_name(),
                               attr['rs1'].data.get_abi_name(), offset),
              file=stream,
              end="")

    else:
        raise Exception(f"Trying to print unknown operation '{op.name}'")

    if 'comment' in attr.keys():
        print(f"    \t# {attr['comment'].data}", file=stream, end="")

    print("", file=stream)


def print_program(instructions, fmt, stream=sys.stdout):
    if fmt == 'mlir':
        printer = Printer()
        for i in instructions:
            printer.print_op(i)
            print("", file=stream)
    else:
        print("\t.data", file=stream)
        print("_heap:\t.space 102400", file=stream)
        print("_heap_tree_ptr:\t.word 100", file=stream)
        print("\t.text", file=stream)
        print("# Initialize the heap memory", file=stream)
        print("\tla t0, _heap", file=stream)
        print("\tla t1, _heap_tree_ptr", file=stream)
        print("\tsw t0, 0(t1)", file=stream)

        for op in instructions:
            print_op(op, stream=stream)

        print("_malloc:", file=stream)
        print("\tla t0, _heap_tree_ptr", file=stream)
        print("\tlw t1, 0(t0)", file=stream)
        print("\tadd t2, t1, a0", file=stream)
        print("\tsw t2, 0(t0)", file=stream)
        print("\taddi a0, t1, 0", file=stream)
        print("\tret", file=stream)

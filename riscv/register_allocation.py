WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
# type: ignore

from __future__ import annotations

from choco.dialects.choco_flat import FuncDef
import riscv.dialect as riscv
from riscv.dialect import RegisterAttr, Register
import riscv.ssa_dialect as riscvssa

from xdsl.ir import ErasedSSAValue, Operation, SSAValue, MLContext
from xdsl.printer import Printer
from xdsl.pattern_rewriter import RewritePattern, PatternRewriter, GreedyRewritePatternApplier, PatternRewriteWalker
from xdsl.dialects.builtin import ModuleOp

from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
from io import StringIO


def allocate_registers(
        func: FuncDef) -> Tuple[int, Dict[SSAValue, int], int, Dict[Op, int]]:
    """
    Allocate each infinite register to a place in the stack.
    returns the number of register spilled, and the position of
    each infinite register on the stack.
    """
    spilled_reg = 0
    stack_vars = 0
    stack_pos = dict()
    alloc_to_stack_var = dict()
    for arg in func.func_body.blocks[0].args:
        stack_pos[arg] = spilled_reg
        spilled_reg += 1
    for op in func.func_body.ops:
        for result in op.results:
            stack_pos[result] = spilled_reg
            spilled_reg += 1
        if isinstance(op, riscvssa.AllocOp):
            alloc_to_stack_var[op] = stack_vars
            stack_vars += 1
    return spilled_reg, stack_pos, stack_vars, alloc_to_stack_var


@dataclass(eq=False)
class RiscvToRiscvSSAPattern(RewritePattern):
    """
    Rewrite a single RISCV_SSA operation into a RISCV operation, given
    the allocation of registers.
    """

    ctx: MLContext
    func: FuncDef
    stack_pos: Dict[SSAValue, int]
    alloc_to_stack_var: Dict[SSAValue, int]
    """Position of the variables on the stack."""
    printer: Printer
    output: StringIO
    global_stack_pos: Optional[Dict[SSAValue, int]] = field(default=None)

    def add_stack_allocation(self,
                             func: FuncOp,
                             spilled_reg: int,
                             stack_vars: int,
                             is_main=False):
        """
        Allocate data on the stack at the beginning of the
        module, and deallocate it at the end.
        """
        header_ops: List[Operation] = [
            riscv.AddIOp.get("sp", "sp", -4, "Reserve space for ra"),
            riscv.SWOp.get("ra", "sp", 0, "Store return address"),
            riscv.AddIOp.get("sp", "sp", -4 * spilled_reg,
                             "Reserve stack space for spilled registers")
        ]
        if stack_vars > 0:
            header_ops.append(
                riscv.AddIOp.get(
                    "sp", "sp", -4 * stack_vars,
                    "Reserve stack space for stack-allocated memory"))
        if is_main:
            header_ops.append(
                riscv.MVOp.get("tp", "sp",
                               "Move main stack pointer to special register"))

        idx = 0
        for arg in func.func_body.blocks[0].args:
            header_ops += self.store_variable_from_register(
                Register.from_name(f"a{idx}"), arg)
            idx += 1

        footer_ops: List[Operation] = [
            riscv.CommentOp.get(""),
            riscv.CommentOp.get("Footer Ops"),
            riscv.LabelOp.get("_" + func.attributes['func_name'].data +
                              "_return"),
            riscv.AddIOp.get(
                "sp", "sp", 4 * spilled_reg,
                "Free stack space reserved for spilled registers")
        ]
        if stack_vars:
            footer_ops.append(
                riscv.AddIOp.get(
                    "sp", "sp", 4 * stack_vars,
                    "Free stack space reserved for stack-allocated memory"))
        footer_ops += [
            riscv.LWOp.get("ra", "sp", 0, "Store return address"),
            riscv.AddIOp.get("sp", "sp", 4, "Free space for ra")
        ]
        block = func.regions[0].blocks[0]
        block.insert_op(header_ops, 0)
        block.insert_op(footer_ops, len(block.ops))

    def get_variable_on_register(self, val: SSAValue,
                                 reg: Register) -> List[Operation]:
        """Place a variable on a specific register."""

        # Get the variable name
        full = self.output.getvalue()
        self.printer._print_operand(val)
        formatted_op = self.output.getvalue()
        formatted_op = formatted_op[len(full):]

        # Get its address if the variable is defined in main
        if val not in self.stack_pos:
            if self.global_stack_pos is None or val not in self.global_stack_pos:
                raise Exception("Critical error in riscv variable allocator.")
            pos = self.global_stack_pos[val]
            if pos * 4 > 2**12:
                raise NotImplementedError(
                    "Register allocator is not working for more than 128 variables."
                )
            op = riscv.LWOp.get(reg, "tp", pos * 4,
                                f"Unspill register '{formatted_op}'")
            return [op]

        pos = self.stack_pos[val]
        if pos * 4 > 2**12:
            raise NotImplementedError(
                "Register allocator is not working for more than 128 variables."
            )

        op = riscv.LWOp.get(reg, "sp", pos * 4,
                            f"Unspill register '{formatted_op}'")
        return [op]

    def store_variable_from_register(self, reg: Register,
                                     val: SSAValue) -> List[Operation]:
        """
        Store a variable into its place in the stack, knowing the
        current position of the variable in the registers.
        """
        pos = self.stack_pos[val]
        if pos * 4 > 2**12:
            raise NotImplementedError(
                "Register allocator is not working for more than 128 variables."
            )
        op = riscv.SWOp.get(reg, "sp", pos * 4, "Spill register")
        return [op]

    def rewrite_ecall(self, op: riscvssa.ECALLOp,
                      rewriter: PatternRewriter) -> None:
        new_ops = []
        new_ops.extend(
            self.get_variable_on_register(op.syscall_num,
                                          Register.from_name("a7")))
        for idx, operand in enumerate(op.args):
            new_ops.extend(
                self.get_variable_on_register(
                    operand, Register.from_name("a" + str(idx))))
        new_ops.append(riscv.ECALLOp.get())
        rewriter.replace_op(op,
                            new_ops, [None] * len(op.results),
                            safe_erase=True)

    def rewrite_call(self, op: riscvssa.CallOp,
                     rewriter: PatternRewriter) -> None:
        new_ops = [riscv.CommentOp.get(""), riscv.CommentOp.get(f"{op.name}")]
        for idx, operand in enumerate(op.args):
            new_ops.extend(
                self.get_variable_on_register(
                    operand, Register.from_name("a" + str(idx))))
        jump = riscv.JALOp.get(Register.from_name("ra"), op.func_name.data)
        new_ops = new_ops + [jump]

        assert len(op.results) in [
            0, 1
        ], "Only functions with zero or one return value supported"

        if len(op.results) == 1:
            new_ops.extend(
                self.store_variable_from_register(Register.from_name('a0'),
                                                  op.results[0]))
        rewriter.replace_op(op,
                            new_ops, [None] * len(op.results),
                            safe_erase=True)

    def rewrite_alloc(self, op: riscvssa.AllocOp,
                      rewriter: PatternRewriter) -> None:
        stack_pos = 4 * (self.alloc_to_stack_var[op] + len(self.stack_pos))
        new_ops = [
            riscv.AddIOp.get(Register.from_name("t0"),
                             Register.from_name("sp"), stack_pos,
                             "Save ptr of stack-slot into register")
        ]
        new_ops.extend(
            self.store_variable_from_register(Register.from_name('t0'),
                                              op.results[0]))
        rewriter.replace_op(op,
                            new_ops, [None] * len(op.results),
                            safe_erase=True)

    def rewrite_return(self, ret: riscvssa.ReturnOp,
                       rewriter: PatternRewriter):
        new_ops = self.get_variable_on_register(ret.value, "a0")
        new_ops.append(
            riscv.JOp.get(
                "_" + ret.parent.parent.parent.attributes['func_name'].data +
                "_return"))
        rewriter.replace_op(ret, new_ops)

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):
        if op.parent.parent.parent is not self.func:
            return

        if isinstance(op, riscvssa.ECALLOp):
            self.rewrite_ecall(op, rewriter)
            return
        if isinstance(op, riscvssa.CallOp):
            self.rewrite_call(op, rewriter)
            return
        if isinstance(op, riscvssa.AllocOp):
            self.rewrite_alloc(op, rewriter)
            return
        if isinstance(op, riscvssa.FuncOp):
            return
        if isinstance(op, riscvssa.ReturnOp):
            self.rewrite_return(op, rewriter)
            return

        # Get the matching operation in RISCV
        name = op.name.split('.', maxsplit=1)
        if len(name) == 1:
            return None
        dialect, opname = name
        if dialect != 'riscv_ssa':
            return None
        new_op_type = self.ctx.get_op('riscv.' + opname)

        full = self.output.getvalue()
        self.printer.print_op(op)
        formatted_op = self.output.getvalue()
        formatted_op = formatted_op[len(full):-1]

        # The operations that will be added
        new_ops = [
            riscv.CommentOp.get(""),
            riscv.CommentOp.get(f"{formatted_op}")
        ]

        # The attributes of the riscv operation that will be created
        new_op_attributes = op.attributes.copy()
        assert len(op.operands) <= 2
        assert len(op.results) <= 1

        # Fill the attributes with the right values for operands and results.
        # Also move operand variables to specific registers.
        if len(op.operands) > 0:
            new_ops.extend(
                self.get_variable_on_register(op.operands[0],
                                              Register.from_name('t1')))
            new_op_attributes['rs1'] = RegisterAttr.from_name('t1')

        if len(op.operands) > 1:
            new_ops.extend(
                self.get_variable_on_register(op.operands[1],
                                              Register.from_name('t2')))
            new_op_attributes['rs2'] = RegisterAttr.from_name('t2')

        if len(op.results) != 0:
            new_op_attributes['rd'] = RegisterAttr.from_name('t0')

        # Create the new corresponding operation
        new_ops.append(new_op_type.create(attributes=new_op_attributes))

        # Place the result in its right place on the stack
        if len(op.results) != 0:
            new_ops.extend(
                self.store_variable_from_register(Register.from_name('t0'),
                                                  op.results[0]))

        rewriter.replace_op(op,
                            new_ops, [None] * len(op.results),
                            safe_erase=True)


def add_print(mod: ModuleOp):
    new_ops = [
        riscv.LabelOp.get("_print_int"),
        riscv.AddIOp.get("sp", "sp", -12),
        riscv.MVOp.get("t1", "a0"),
        riscv.LIOp.get("t2", 10),
        riscv.SLTIOp.get("t6", "t1", 0),
        riscv.SLTIOp.get("t6", "t1", 0),
        riscv.LIOp.get("t5", 2),
        riscv.MULOp.get("t6", "t5", "t6"),
        riscv.LIOp.get("t5", 1),
        riscv.SubOp.get("t5", "t5", "t6"),
        riscv.MULOp.get("t1", "t5", "t1"),
        riscv.MVOp.get("t6", "zero"),
    ]

    for idx in range(10, 1, -1):
        new_ops += [
            riscv.REMOp.get("t0", "t1", "t2"),
            riscv.AddIOp.get("t0", "t0", 48),
            riscv.SLTIOp.get("t3", "t1", 1),
            riscv.AddOp.get("t6", "t6", "t3"),
            riscv.SBOp.get("t0", "sp", idx),
            riscv.DIVOp.get("t1", "t1", "t2"),
        ]

    new_ops += [
        riscv.REMOp.get("t0", "t1", "t2"),
        riscv.AddIOp.get("t0", "t0", 48),
        riscv.SLTIOp.get("t3", "t1", 1),
        riscv.SLTOp.get("t4", "zero", "a0"),
        riscv.SLTOp.get("t5", "a0", "zero"),
        riscv.OROp.get("t4", "t4", "t5"),
        riscv.ANDOp.get("t3", "t3", "t4"),
        riscv.AddOp.get("t6", "t6", "t3"),
        riscv.SBOp.get("t0", "sp", 1),
        riscv.DIVOp.get("t1", "t1", "t2"),
    ]

    new_ops += [
        riscv.SLTIOp.get("t5", "t5", -1),
        riscv.AddOp.get("t6", "t6", "t5"),
        riscv.LIOp.get("t5", 45),
        riscv.AddOp.get("t4", "sp", "t6"),
        riscv.SBOp.get("t5", "t4", 0),
        riscv.LIOp.get("t4", -1),
        riscv.SLTOp.get("t3", "t4", "a0"),
        riscv.AddOp.get("t6", "t6", "t3"),
    ]

    new_ops += [
        riscv.LIOp.get("t0", 10),
        riscv.SBOp.get("t0", "sp", 11),
        riscv.LIOp.get("a0", 1),
        riscv.MVOp.get("a1", "sp"),
        riscv.AddOp.get("a1", "a1", "t6"),
        riscv.LIOp.get("a2", 12),
        riscv.SubOp.get("a2", "a2", "t6"),
        riscv.LIOp.get("a7", 64),
        riscv.ECALLOp.get(),
        riscv.AddIOp.get("sp", "sp", 12),
        riscv.RETOp.get(),
    ]

    mod.regions[0].blocks[0].add_ops(new_ops)
    return mod


def add_input(mod: ModuleOp):
    new_ops = [
        riscv.LabelOp.get("_input"),
        riscv.AddIOp.get("sp", "sp", -1024),
        riscv.SWOp.get("ra", "sp", 1020),
        riscv.LIOp.get("a0", 0),
        riscv.MVOp.get("a1", "sp"),
        riscv.LIOp.get("a2", 1020),
        riscv.LIOp.get("a7", 63),
        riscv.ECALLOp.get(),
        riscv.LIOp.get("t1", 4),
        riscv.MVOp.get("t4", "a0"),
        riscv.AddIOp.get("t4", "t4", -1),
        riscv.MULOp.get("a0", "a0", "t1"),
        riscv.AddOp.get("a0", "a0", "t1"),
        riscv.JALOp.get("ra", "_malloc", "Allocate memory for new list"),
        riscv.LIOp.get("t1", 4),
        riscv.SWOp.get("t4", "a0", 0),
        riscv.LIOp.get("t5", 0),
        riscv.BEQOp.get("t4", "t5", "_input_loop_finished"),
        riscv.LabelOp.get("_input_loop_header"),
        riscv.AddOp.get("t3", "sp", "t5"),
        riscv.LBOp.get("t6", "t3", 0),
        riscv.MULOp.get("t3", "t5", "t1"),
        riscv.AddOp.get("t3", "a0", "t3"),
        riscv.SWOp.get("t6", "t3", 4),
        riscv.AddIOp.get("t5", "t5", 1),
        riscv.BNEOp.get("t4", "t5", "_input_loop_header"),
        riscv.LabelOp.get("_input_loop_finished"),
        riscv.LWOp.get("ra", "sp", 1020),
        riscv.AddIOp.get("sp", "sp", 1024),
        riscv.RETOp.get(),
    ]

    mod.regions[0].blocks[0].add_ops(new_ops)
    return mod


def string_on_stack_ops(message: str) -> Tuple[int, List[Operation]]:
    # We align the stack to 4 bytes
    num_stack_space = len(message) + (4 - len(message)) % 4
    ops = [riscv.AddIOp.get("sp", "sp", -num_stack_space)]
    for idx, char in enumerate(message):
        ops.append(riscv.LIOp.get("t0", ord(char)))
        ops.append(riscv.SBOp.get("t0", "sp", idx))
    return num_stack_space, ops


def print_message_ops(message: str) -> List[Operation]:
    string_size, string_ops = string_on_stack_ops(message)
    new_ops = string_ops + [
        riscv.LIOp.get("a0", 1),  # stdout stream
        riscv.MVOp.get("a1", "sp"),  # string pointer
        riscv.LIOp.get("a2", len(message)),  # string size
        riscv.LIOp.get("a7", 64),  # print string code
        riscv.ECALLOp.get(),
        riscv.AddIOp.get("sp", "sp", string_size),
    ]
    return new_ops


def add_print_bool(mod: ModuleOp):
    string_size, string_ops = string_on_stack_ops("False\n\0True\n\0")
    new_ops = [
        riscv.LabelOp.get("_print_bool"),
    ] + string_ops + [
        riscv.LIOp.get("t1", 7),
        riscv.SLTUOp.get("t2", "zero", "a0"),
        riscv.MULOp.get("t1", "t1", "t2"),
        riscv.AddOp.get("t1", "t1", "sp"),
        riscv.LIOp.get("t3", 6),
        riscv.SLTUOp.get("t4", "zero", "a0"),
        riscv.SubOp.get("t4", "t3", "t4"),
        riscv.LIOp.get("a0", 1),
        riscv.MVOp.get("a1", "t1"),
        riscv.MVOp.get("a2", "t4"),
        riscv.LIOp.get("a7", 64),
        riscv.ECALLOp.get(),
        riscv.AddIOp.get("sp", "sp", string_size),
        riscv.RETOp.get(),
    ]

    mod.regions[0].blocks[0].add_ops(new_ops)
    return mod


def add_print_string(mod: ModuleOp):
    new_ops = [
        riscv.LabelOp.get("_print_str"),
        riscv.AddIOp.get("t0", "a0", 0, "Get address of string object"),
        riscv.LWOp.get("t2", "t0", 0, "Load length of string"),
        riscv.LIOp.get("t1", 0, "Set loop counter to zero"),
        riscv.SubOp.get("sp", "sp", "t2",
                        "Expand stack pointer by number of string elements"),
        riscv.AddIOp.get("sp", "sp", -1, "Expand stack pointer for newline"),
        riscv.BEQOp.get("t1", "t2", "_print_str_loop_finished"),
        riscv.LabelOp.get("_print_str_loop_header"),
        riscv.LIOp.get("t6", 4, "Number of bytes per element"),
        riscv.MULOp.get("t3", "t1", "t6", "Distance from pointer in bytes"),
        riscv.AddOp.get("t4", "t0", "t3",
                        "The address of the element in the string"),
        riscv.LWOp.get("t5", "t4", 4),
        riscv.AddOp.get("t4", "sp", "t1",
                        "The address of the element on the stack"),
        riscv.SBOp.get("t5", "t4", 0, "Store character on stack"),
        riscv.AddIOp.get("t1", "t1", 1, "Increment loop counter"),
        riscv.BNEOp.get("t1", "t2", "_print_str_loop_header", "Continue loop"),
        riscv.LabelOp.get("_print_str_loop_finished"),
        riscv.AddOp.get("t4", "sp", "t1",
                        "The address of the element on the stack"),
        riscv.LIOp.get("t5", ord("\n"),
                       "Store newline character in output string"),
        riscv.SBOp.get("t5", "t4", 0, "Store character on stack"),
        riscv.LIOp.get("a0", 1, "Print to stdout"),
        riscv.MVOp.get(
            "a1", "sp",
            "syscall argument: the start address is the stack pointer"),
        riscv.AddIOp.get("t3", "t2", 1, "Make room for newline"),
        riscv.MVOp.get("a2", "t3", "syscall argument: length of the string"),
        riscv.LIOp.get("a7", 64, "Request the print system call"),
        riscv.ECALLOp.get("Trigger the system call"),
        riscv.AddIOp.get("sp", "sp", 1, "Free the stack for newline"),
        riscv.AddOp.get("sp", "sp", "t2", "Free the stack"),
        riscv.RETOp.get(),
    ]

    mod.regions[0].blocks[0].add_ops(new_ops)
    return mod


def add_print_error(mod: ModuleOp, func_name: str, message: str):
    new_ops = [riscv.LabelOp.get(func_name)
               ] + print_message_ops(message) + exit_ops(1)
    mod.regions[0].blocks[0].add_ops(new_ops)


def add_list_concat(mod: ModuleOp):
    new_ops = [
        riscv.LabelOp.get("_list_concat"),
        riscv.AddIOp.get("sp", "sp", -24, "Reserve stack space"),
        riscv.LWOp.get("t0", "a0", 0, "Load length of list a"),
        riscv.LWOp.get("t1", "a1", 0, "Load length of list b"),
        riscv.AddOp.get("t2", "t0", "t1", "Compute length of overall list"),
        riscv.LIOp.get("t3", 4, "Load size of a word in bytes"),
        riscv.MULOp.get("t4", "t2", "t3",
                        "Compute amount of storage for list elements"),
        riscv.AddIOp.get("t4", "t4", 4,
                         "Also consider space needed to store list size"),
        riscv.SWOp.get("ra", "sp", 0, "Save return address"),
        riscv.SWOp.get("t0", "sp", 4, "Save length of list a"),
        riscv.SWOp.get("t1", "sp", 8, "Save length of list b"),
        riscv.SWOp.get("t2", "sp", 12, "Save length of new list"),
        riscv.SWOp.get("a0", "sp", 16, "Save base ptr of list a"),
        riscv.SWOp.get("a1", "sp", 20, "Save base ptr of list b"),
        riscv.AddIOp.get("a0", "t4", 0),
        riscv.JALOp.get("ra", "_malloc", "Allocate memory for new list"),
        riscv.LWOp.get("ra", "sp", 0, "Restore return address"),
        riscv.LWOp.get("t0", "sp", 4, "Restore length of list a"),
        riscv.LWOp.get("t1", "sp", 8, "Restore length of list b"),
        riscv.LWOp.get("t2", "sp", 12, "Restore length of new list"),
        riscv.LWOp.get("t3", "sp", 16, "Restore base ptr of list a"),
        riscv.LWOp.get("t4", "sp", 20, "Restore base ptr of list b"),
        riscv.SWOp.get("t2", "a0", 0, "Store length of new list in list"),
        riscv.LIOp.get("t5", 0, "Set loop counter"),
        riscv.AddIOp.get("t6", "a0", 0),
        riscv.BEQOp.get("t0", "zero", "_list_concat_repeat_first_end"),
        riscv.LabelOp.get("_list_concat_repeat_first"),
        riscv.AddIOp.get("t5", "t5", 1),
        riscv.AddIOp.get("t3", "t3", 4),
        riscv.AddIOp.get("t6", "t6", 4),
        riscv.LWOp.get("t2", "t3", 0, "Load list element from a"),
        riscv.SWOp.get("t2", "t6", 0, "Store list element in new list"),
        riscv.BNEOp.get("t5", "t0", "_list_concat_repeat_first"),
        riscv.LabelOp.get("_list_concat_repeat_first_end"),
        riscv.LIOp.get("t5", 0, "Set loop counter"),
        riscv.BEQOp.get("t1", "zero", "_list_concat_repeat_second_end"),
        riscv.LabelOp.get("_list_concat_repeat_second"),
        riscv.AddIOp.get("t5", "t5", 1),
        riscv.AddIOp.get("t4", "t4", 4),
        riscv.AddIOp.get("t6", "t6", 4),
        riscv.LWOp.get("t2", "t4", 0, "Load list element from a"),
        riscv.SWOp.get("t2", "t6", 0, "Store list element in new list"),
        riscv.BNEOp.get("t5", "t1", "_list_concat_repeat_second"),
        riscv.LabelOp.get("_list_concat_repeat_second_end"),
        riscv.AddIOp.get("sp", "sp", 24, "Free stack space"),
        riscv.RETOp.get()
    ]

    mod.regions[0].blocks[0].add_ops(new_ops)
    return mod


def add_str_eq(mod: ModuleOp):
    new_ops = [
        riscv.LabelOp.get("_str_eq"),
        riscv.LWOp.get("t0", "a0", 0, "Load length of first string"),
        riscv.LWOp.get("t1", "a1", 0, "Load length of second string"),
        riscv.BNEOp.get("t0", "t1", "_str_eq_return_false",
                        "return false if length are not equal"),
        riscv.BEQOp.get("t0", "zero", "_str_eq_return_true",
                        "return true if both length are equal to 0"),
        riscv.AddIOp.get("t2", "a0", 4, "First string index iterator"),
        riscv.AddIOp.get("t3", "a1", 4, "Second string index iterator"),
        riscv.LIOp.get("t5", 4, "Size of an integer"),
        riscv.MULOp.get("t5", "t0", "t5", "Size of the strings in bytes"),
        riscv.AddOp.get("t4", "a0", "t5",
                        "First string iterator last element"),
        riscv.AddIOp.get("t4", "t4", 4, "First string end iterator"),
        riscv.LabelOp.get("_str_eq_loop_begin"),
        riscv.LWOp.get("t5", "t2", 0, "Get the first string character"),
        riscv.LWOp.get("t6", "t3", 0, "Get the first string character"),
        riscv.BNEOp.get("t5", "t6", "_str_eq_return_false",
                        "If the characters are different, return false"),
        riscv.AddIOp.get("t2", "t2", 4),
        riscv.AddIOp.get("t3", "t3", 4),
        riscv.BLTOp.get("t2", "t4", "_str_eq_loop_begin",
                        "If we are not at the end of the string, continue"),
        riscv.LabelOp.get("_str_eq_return_true"),
        riscv.LIOp.get("a0", 1),
        riscv.RETOp.get(),
        riscv.LabelOp.get("_str_eq_return_false"),
        riscv.LIOp.get("a0", 0),
        riscv.RETOp.get()
    ]

    mod.regions[0].blocks[0].add_ops(new_ops)
    return mod


def exit_ops(exit_code: int) -> List[Operation]:
    return [
        riscv.CommentOp.get(""),
        riscv.CommentOp.get("Exit program"),
        riscv.LIOp.get("a0", exit_code),
        riscv.LIOp.get("a7", 93),
        riscv.ECALLOp.get(),
    ]


def add_exit(mod: ModuleOp):
    mod.regions[0].blocks[0].add_ops(exit_ops(0))


def add_return(op: Operation):
    new_ops = [riscv.RETOp.get()]

    op.regions[0].blocks[0].add_ops(new_ops)


def riscv_ssa_to_riscv(ctx: MLContext, mod: ModuleOp):
    """
    Translate a riscvssa program into an equivalent RISCV program.
    """

    output = StringIO()
    printer = Printer(output, )
    printer.print_op(mod)

    assert len(mod.ops) == 1, "expected at least one main function"
    main = mod.ops[0]

    global_spilled_reg, global_stack_pos, global_stack_vars, global_alloc_to_stack_var = allocate_registers(
        main)

    # Allocate registers in all function definitions
    for func in main.func_body.ops:
        if not isinstance(func, riscvssa.FuncOp):
            continue
        spilled_reg, stack_pos, stack_vars, alloc_to_stack_var = allocate_registers(
            func)
        pattern = RiscvToRiscvSSAPattern(ctx,
                                         func,
                                         stack_pos,
                                         alloc_to_stack_var,
                                         printer,
                                         output,
                                         global_stack_pos=global_stack_pos)
        pattern.add_stack_allocation(func, spilled_reg, stack_vars)
        add_return(func)
        walker = PatternRewriteWalker(GreedyRewritePatternApplier([pattern]),
                                      apply_recursively=True,
                                      walk_reverse=True)
        walker.rewrite_module(func)

    # Allocate registers in the main function
    pattern = RiscvToRiscvSSAPattern(ctx, main, global_stack_pos,
                                     global_alloc_to_stack_var, printer,
                                     output)
    pattern.add_stack_allocation(main,
                                 global_spilled_reg,
                                 global_stack_vars,
                                 is_main=True)
    walker = PatternRewriteWalker(GreedyRewritePatternApplier([pattern]),
                                  apply_recursively=True,
                                  walk_reverse=True)
    walker.rewrite_module(main)
    add_exit(main)

    add_print(mod)
    add_print_bool(mod)
    add_print_string(mod)
    add_input(mod)
    add_list_concat(mod)
    add_str_eq(mod)
    add_print_error(mod, "_error_len_none",
                    "TypeError: object of type 'NoneType' has no len()")
    add_print_error(mod, "_list_index_oob",
                    "IndexError: list index out of range")
    add_print_error(mod, "_list_index_none",
                    "TypeError: 'NoneType' object is not subscriptable")
    add_print_error(mod, "_error_div_zero", "DivByZero: Division by zero")
    for func in main.func_body.ops:
        if not isinstance(func, riscvssa.FuncOp):
            continue
        func.detach()
        main.func_body.blocks[0].add_op(func)

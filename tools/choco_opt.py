WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
#!/usr/bin/env python3

import argparse
import ast
from io import IOBase

from xdsl.ir import MLContext
from xdsl.dialects.builtin import ModuleOp

from choco.check_assign_target import check_assign_target
from choco.for_to_while import for_to_while
from choco.name_analysis import name_analysis
from choco.type_checking import type_checking
from choco.warn_dead_code import DeadCodeError, warn_dead_code
from riscv.dialect import RISCV
from riscv.printer import print_program
from riscv.register_allocation import riscv_ssa_to_riscv
from riscv.function_lowering import riscv_function_lowering
from riscv.ssa_dialect import RISCVSSA
from choco.choco_ast_to_choco_flat import choco_ast_to_choco_flat
from choco.constant_folding import choco_flat_constant_folding
from choco.dead_code_elimination import choco_flat_dead_code_elimination
from choco.choco_flat_introduce_library_calls import choco_flat_introduce_library_calls

from choco.choco_flat_to_riscv_ssa import choco_flat_to_riscv_ssa

from choco.lexer import Lexer as ChocoLexer
from choco.parser import Parser as ChocoParser
from choco.parser import SyntaxError

from choco.semantic_error import SemanticError

from choco.dialects.choco_ast import ChocoAST
from choco.dialects.choco_flat import ChocoFlat

from typing import Callable, Dict, List

from xdsl.xdsl_opt_main import xDSLOptMain


class ChocoOptMain(xDSLOptMain):

    passes_native = [
        # Semantic Analysis
        check_assign_target,
        name_analysis,
        type_checking,
        warn_dead_code,

        # IR Generation
        choco_ast_to_choco_flat,

        # IR Optimization
        choco_flat_introduce_library_calls,
        choco_flat_constant_folding,
        choco_flat_dead_code_elimination,
        for_to_while,

        # Code Generation
        choco_flat_to_riscv_ssa,
        riscv_ssa_to_riscv,
        riscv_function_lowering,
    ]

    def register_all_passes(self):
        self.available_passes = self.get_passes_as_dict()

    def _output_risc(self, prog: ModuleOp, output: IOBase):
        print_program(prog.ops, "riscv", stream=output)  #type: ignore

    def register_all_targets(self):
        super().register_all_targets()
        self.available_targets['riscv'] = lambda prog, output: print_program(
            prog.ops, "riscv", stream=output)  #type: ignore

    def pipeline_entry(self, k: str, entries: Dict):
        """Helper function that returns a pass"""
        if k in entries.keys():
            return entries[k]

    def setup_pipeline(self):

        entries = {
            'type': 'type-checking',
            'warn': 'warn-dead-code',
            'ir': 'choco-ast-to-choco-flat',
            'fold': 'choco-flat-constant-folding',
            'riscv': 'choco-flat-to-riscv-ssa'
        }

        if self.args.passes != 'all':
            if self.args.passes in entries:
                pipeline = self.get_passes_as_list(native=True)
                entry = self.pipeline_entry(self.args.passes, entries)
                if entry not in ['type', 'warn', 'fold', 'warn-dead-code']:
                    # the case where our entry is warn-dead-code only
                    pipeline = list(
                        filter(lambda x: x != 'warn-dead-code', pipeline))
                pipeline = pipeline[:pipeline.index(entry) + 1]  # type: ignore
            else:
                super().setup_pipeline()
                return

        else:
            pipeline = self.get_passes_as_list(native=True)
            # Disable dead code warnings to not litter the asm code output.
            pipeline = list(filter(lambda x: x != 'warn-dead-code', pipeline))

        self.pipeline = [(p, lambda op, p=p: self.available_passes[p]
                          (self.ctx, op)) for p in pipeline]

    def register_all_dialects(self):
        super().register_all_dialects()
        """Register all dialects that can be used."""
        self.ctx.register_dialect(RISCV)
        self.ctx.register_dialect(RISCVSSA)
        self.ctx.register_dialect(ChocoAST)
        self.ctx.register_dialect(ChocoFlat)

    @staticmethod
    def get_passes_as_dict(
    ) -> Dict[str, Callable[[MLContext, ModuleOp], None]]:
        """Add all passes that can be called by choco-opt in a dictionary."""

        pass_dictionary = {}

        passes = ChocoOptMain.passes_native

        for pass_function in passes:
            pass_dictionary[pass_function.__name__.replace(
                "_", "-")] = pass_function

        return pass_dictionary

    def get_passes_as_list(self, native: bool = False) -> List[str]:
        """Add all passes that can be called by choco-opt in a list."""

        pass_list = []

        if native:
            passes = ChocoOptMain.passes_native
        else:
            passes = ChocoOptMain.passes_native
        for pass_function in passes:
            pass_list.append(pass_function.__name__.replace("_", "-"))

        return pass_list

    def register_all_frontends(self):
        super().register_all_frontends()

        def parse_choco(f: IOBase):
            lexer = ChocoLexer(f)  # type: ignore
            parser = ChocoParser(lexer)
            program = parser.parse_program()
            return program

        self.available_frontends['choc'] = parse_choco


def __main__():
    choco_main = ChocoOptMain()

    try:
        module = choco_main.parse_input()
        choco_main.apply_passes(module)
    except SyntaxError as e:
        print(e.get_message())
        exit(0)
    except SemanticError as e:
        print("Semantic error: %s" % str(e))
        exit(0)
    except DeadCodeError as e:
        print(f"[Warning] Dead code found: {e}")
        exit(0)

    contents = choco_main.output_resulting_program(module)
    choco_main.print_to_output_stream(contents)


if __name__ == "__main__":
    __main__()

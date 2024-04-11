WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from __future__ import annotations
from typing import Dict
from xdsl.dialects.builtin import ModuleOp
from choco.ast_visitor import Visitor
from choco.dialects.choco_ast import *
from dataclasses import dataclass, field

from choco.semantic_error import SemanticError


def name_analysis(_: MLContext, module: ModuleOp) -> ModuleOp:

    @dataclass
    class NameCtx:
        """
        Scoped context of names.
        """
        names: Dict[str, Optional[NameCtx]] = field(default_factory=dict)
        parent_scope: Optional[NameCtx] = None

        def contains_in_scope(self, name: str) -> bool:
            if name in self.names:
                return True
            else:
                return False

        def contains_in_parent_scope(self, name: str) -> bool:
            if self.parent_scope:
                return self.parent_scope.contains_in_scope(
                    name) or self.parent_scope.contains_in_parent_scope(name)
            else:
                return False

        def add_var(self, name: str):
            if name in self.names:
                raise SemanticError(
                    f"[Name Analysis Error]: "
                    f"Identifier {name} already defined in the current context"
                )
            else:
                self.names[name] = None

        def add_func(self, name: str, nested_ctx: NameCtx):
            if name in self.names:
                raise SemanticError(
                    f"[Name Analysis Error]: "
                    f"Identifier {name} already defined in the current context"
                )
            else:
                self.names[name] = nested_ctx

        def get_func_ctx(self, name: str) -> NameCtx:
            ret = self.names.get(name)
            if ret is None:
                raise SemanticError(
                    f"[Name Analysis Error]: "
                    f"Function {name} found that was not previously defined.")
            else:
                return ret

        def global_scope(self) -> NameCtx:
            if self.parent_scope is None:
                return self

            return self.parent_scope.global_scope()

    @dataclass
    class BuildContextVisitor(Visitor):
        name_ctx: NameCtx

        def visit_var_def(self, var_def: VarDef):
            """
            Add the defined variable to the context
            """
            typed_var = var_def.typed_var.blocks[0].ops[0]
            assert isinstance(typed_var, TypedVar)
            self.name_ctx.add_var(typed_var.var_name.data)  #type: ignore

        def traverse_func_def(self, func_def: FuncDef):
            """
            Add the function name to the current name context and the parameter names to a nested name context.
            Traverse the function body with the nested name context.
            """
            body_visitor = BuildContextVisitor(
                NameCtx(parent_scope=self.name_ctx))

            for op in func_def.params.blocks[0].ops:
                assert isinstance(op, TypedVar)
                body_visitor.name_ctx.add_var(op.var_name.data)  #type: ignore

            for op in func_def.func_body.blocks[0].ops:
                if isinstance(op, GlobalDecl):
                    body_visitor.name_ctx.add_var(
                        op.decl_name.data)  #type: ignore
                if isinstance(op, NonLocalDecl):
                    body_visitor.name_ctx.add_var(
                        op.decl_name.data)  #type: ignore

            for op in func_def.func_body.blocks[0].ops:
                body_visitor.traverse(op)

            self.name_ctx.add_func(
                func_def.func_name.data,  #type: ignore
                body_visitor.name_ctx)

    @dataclass
    class NameAnalysisVisitor(Visitor):
        """
        Visit all identifiers in the expression and change the default traversal behaviour
        for variable definitions and function definitions.
        """
        name_ctx: NameCtx

        def visit_expr_name(self, expr_name: ExprName):
            """
            For each variable name check that it has been declared before
            """
            name = expr_name.id.data  #type: ignore
            if self.name_ctx.contains_in_scope(
                    name) or self.name_ctx.contains_in_parent_scope(name):
                return

            raise SemanticError(
                f'[Name Analysis Error]: '
                f"Identifier `{name}' found that was not previously defined.")

        def visit_call_expr(self, call_expr: CallExpr):
            """
            For each function call check that the function has been declared before
            """
            name = call_expr.func.data  #type: ignore
            if self.name_ctx.contains_in_scope(
                    name) or self.name_ctx.contains_in_parent_scope(name):
                return

            raise SemanticError(
                f'[Name Analysis Error]: '
                f"Identifier `{name}' found that was not previously defined.")

        def traverse_func_def(self, func_def: FuncDef):
            """
            Add the function name to the current name context and the parameter names to a nested name context.
            Traverse the function body with the nested name context.
            """
            nested_ctx = self.name_ctx.get_func_ctx(
                func_def.func_name.data)  #type: ignore

            body_visitor = NameAnalysisVisitor(nested_ctx)

            for op in func_def.func_body.blocks[0].ops:
                body_visitor.traverse(op)

        def traverse_for(self, for_op: For):
            """
            Check that the variable of a for loop has been declared in the local scope.
            """
            if not self.name_ctx.contains_in_scope(
                    for_op.iter_name.data):  #type: ignore
                raise SemanticError(
                    f'[Name Analysis Error]: '
                    f"Identifier `{for_op.iter_name.data}' found that was not previously defined."  #type: ignore
                )
            self.traverse(for_op.iter.blocks[0].ops[0])
            for op in for_op.body.blocks[0].ops:
                self.traverse(op)

        def visit_assign(self, assign: Assign):
            """
            Check that assignment variable has been declared in the local scope.
            """
            target_op = assign.target.op
            if isinstance(target_op, ExprName):
                name = target_op.id.data  #type: ignore
                if self.name_ctx.contains_in_scope(name):
                    return
                raise SemanticError(
                    f'[Name Analysis Error]: '
                    f"Cannot assign to variable `{name}' that is not explicitly declared in this scope"
                )

        def visit_global_decl(self, global_decl: GlobalDecl):
            """
            Check that the variable is declared in the global scope.
            """
            if self.name_ctx.global_scope().contains_in_scope(
                    global_decl.decl_name.data):  #type: ignore
                return

            raise SemanticError(
                f'[Name Analysis Error]: '
                f"Identifier `{global_decl.decl_name.data}' not declared in global scope."  #type: ignore
            )

        def visit_non_local_decl(self, non_local_decl: NonLocalDecl):
            """
            Check that the variable is declared in the parent scope and that the parent scope is not the global scope.
            """
            non_local_declare = non_local_decl.decl_name.data  #type:ignore
            if self.name_ctx.parent_scope and self.name_ctx.parent_scope.contains_in_scope(non_local_declare) \
                    and self.name_ctx.parent_scope != self.name_ctx.global_scope():  #type: ignore
                return  #type: ignore

            raise SemanticError(
                f'[Name Analysis Error]: '
                f"Identifier `{non_local_decl.decl_name.data}' not declared in valid parent scope."  #type: ignore
            )

    # add print, len, and input functions to the global context
    name_ctx = NameCtx()
    name_ctx.add_func("print", NameCtx())
    name_ctx.add_func("len", NameCtx())
    name_ctx.add_func("input", NameCtx())

    BuildContextVisitor(name_ctx).traverse(module)
    NameAnalysisVisitor(name_ctx).traverse(module)

    return module

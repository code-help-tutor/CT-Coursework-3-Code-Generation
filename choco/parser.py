WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from xdsl.dialects.builtin import ModuleOp

from choco.lexer import Token, TokenKind, Lexer
import choco.dialects.choco_ast as ast

from xdsl.ir import Operation
from typing import List, Union


class SyntaxError(Exception):

    def __init__(self, row, column, message, line):
        # Rows and columns are counted from zero, but printed counting from one.
        self.row = row
        self.column = column
        self.message = message
        self.line = line

    def get_message(self):
        # The printed row and colum count starts at 1
        printed_line = self.row + 1
        printed_column = self.column + 1
        s = f"SyntaxError (line {printed_line}, column {printed_column}): {self.message}.\n"
        s += ">>>" + self.line + "\n"
        s += ">>>" + self.column * "-" + "^"
        return s


class Parser:
    """
    A Simple ChocoPy Parser

    Parse the given tokens from the lexer and call the xDSL API to create an AST.
    """

    def __init__(self, lexer: Lexer):
        """
        Create a new parser.

        Initialize parser with the corresponding lexer.
        """
        self.lexer = lexer

    def check(self, expected: Union[List[TokenKind], TokenKind]) -> bool:
        """
        Check that the next token is of a given kind. If a list of n TokenKinds
        is given, check that the next n TokenKinds match the next expected
        ones.

        :param expected: The kind of the token we expect or a list of expected
                         token kinds if we look ahead more than one token at
                         a time.
        :returns: True if the next token has the expected token kind, False
￼                 otherwise.
        """

        if isinstance(expected, list):
            tokens = self.lexer.peek(len(expected))
            assert isinstance(tokens, list), "List of tokens expected"
            return all(
                [tok.kind == type_ for tok, type_ in zip(tokens, expected)])

        token = self.lexer.peek()
        assert isinstance(token, Token), "Single token expected"
        return token.kind == expected

    def match(self, expected: TokenKind) -> Token:
        """
        Match a token by first checking the token kind. In case the token is of
        the expected kind, we consume the token.  If a token with an unexpected
        token kind is encountered, an error is reported by raising an
        exception.

        The exception shows information about the line where the token was expected.

        :param expected: The kind of the token we expect.
        :returns: The consumed token if the next token has the expected token
                  kind, otherwise a parsing error is reported.
        """

        if self.check(expected):
            token = self.lexer.peek()
            assert isinstance(token, Token), "A single token expected"
            self.lexer.consume()
            return token

        self.error(f"token of kind {expected} not found")

    def error(self, message):
        token = self.lexer.peek()
        assert isinstance(token, Token), "A single token expected"
        line_num = self.lexer.tokenizer.line_number

        # If NEWLINE was the wrong token found, we need to rewind the line number by 1.
        if token.kind == TokenKind.NEWLINE:
            line_num -= 1

        column = token.column

        # Consume all tokens until the end of the line
        while (token.kind != TokenKind.NEWLINE
               and token.kind != TokenKind.EOF):
            self.lexer.consume()
            token = self.lexer.peek()
            assert isinstance(token, Token), "A single token expected"

        line = self.lexer.tokenizer.scanner.line_buffer
        line = line.replace('\n', '')
        raise SyntaxError(line_num, column, message, line)

    def parse_program(self) -> ModuleOp:
        """
        Parse a ChocoPy program.

        program ::= def_seq stmt_seq EOF

        :returns: The AST of a ChocoPy Program.
        """
        if self.check(TokenKind.INDENT):
            self.error("Unexpected indentation")

        defs = self.parse_def_seq()

        if self.check(TokenKind.INDENT):
            self.error("Unexpected indentation")

        stmts = self.parse_stmt_seq()

        self.match(TokenKind.EOF)

        return ModuleOp.from_region_or_ops([ast.Program.get(defs, stmts)])

    def parse_def_seq(self) -> List[Operation]:
        """
        Parse a sequence of function and variable definitions.

        def_seq ::= [func_def | var_def]*

        :returns: A list of function and variable definitions.
        """

        defs: List[Operation] = []

        while self.check(TokenKind.CLASS) or self.check(
                TokenKind.DEF) or self.check(
                    [TokenKind.IDENTIFIER, TokenKind.COLON]):
            if self.check(TokenKind.CLASS):
                assert False, "Classes not yet supported"
            if self.check(TokenKind.DEF):
                func_def = self.parse_function()
                defs.append(func_def)
                continue
            if self.check(TokenKind.IDENTIFIER):
                var_def = self.parse_var_def()
                defs.append(var_def)
                continue

        return defs

    def parse_function(self) -> Operation:
        """
        Parse a function definition.

                   func_def := `def` ID `(` func_params `)` func_type `:` NEWLINE INDENT func_body DEDENT
                func_params := typed_var
                             | typed_var typed_var_list_tail
                             | epsilon
        typed_var_list_tail := `,` typed_var typed_var_list_tail
                             | epsilon
                  func_type := `->` type
                             | epsilon
                  func_body := decl_seq stmt_seq
                  decl_seq  := decl decl_seq
                             | epsilon
                       decl := func_def

        :return: Operation
        """
        self.match(TokenKind.DEF)

        function_name = self.match(TokenKind.IDENTIFIER)

        self.match(TokenKind.LROUNDBRACKET)

        # Function parameters
        parameters: List[Operation] = []
        if self.check(TokenKind.IDENTIFIER):
            parameters.append(self.parse_typed_var())
            while self.check(TokenKind.COMMA):
                self.match(TokenKind.COMMA)
                parameters.append(self.parse_typed_var())

        if self.is_expr_first_set():
            self.error("expression found, but comma expected")

        self.match(TokenKind.RROUNDBRACKET)

        # Return type: default is <None>.
        return_type = ast.TypeName.get('<None>')
        if self.check(TokenKind.RARROW):
            self.match(TokenKind.RARROW)
            return_type = self.parse_type()

        self.match(TokenKind.COLON)

        self.match(TokenKind.NEWLINE)

        if not self.check(TokenKind.INDENT):
            self.error("expected at least one indented statement in function")

        self.match(TokenKind.INDENT)

        defs_and_decls: List[Operation] = []
        while (self.check([TokenKind.IDENTIFIER, TokenKind.COLON])
               or self.check(TokenKind.GLOBAL)
               or self.check(TokenKind.NONLOCAL)):
            if self.check([TokenKind.IDENTIFIER, TokenKind.COLON]):
                var_def = self.parse_var_def()
                defs_and_decls.append(var_def)
            elif self.check(TokenKind.GLOBAL):
                global_decl = self.parse_global_decl()
                defs_and_decls.append(global_decl)
            elif self.check(TokenKind.NONLOCAL):
                nonlocal_decl = self.parse_nonlocal_decl()
                defs_and_decls.append(nonlocal_decl)

        if self.check(TokenKind.INDENT):
            self.error("Unexpected indentation")

        if self.check(TokenKind.DEDENT):
            self.error("expected at least one indented statement in function")

        stmt_seq = self.parse_stmt_seq()

        func_body = defs_and_decls + stmt_seq

        self.match(TokenKind.DEDENT)

        return ast.FuncDef.get(function_name.value, parameters, return_type,
                               func_body)

    def parse_typed_var(self) -> Operation:
        """
        Parse a typed variable

        typed_var := ID : type
        :return: Operation
        """
        var_name = self.match(TokenKind.IDENTIFIER).value
        self.match(TokenKind.COLON)
        type_ = self.parse_type()
        return ast.TypedVar.get(var_name, type_)

    def parse_type(self) -> Operation:
        """
        Parse one of the builtin types or a list of a type

        type := ID | [type]

        Supported builtin types: object, int, bool, str
        :return: Operation
        """
        type_name = ''
        if self.check(TokenKind.OBJECT):
            self.match(TokenKind.OBJECT)
            type_name = 'object'
        elif self.check(TokenKind.INT):
            self.match(TokenKind.INT)
            type_name = 'int'
        elif self.check(TokenKind.BOOL):
            self.match(TokenKind.BOOL)
            type_name = 'bool'
        elif self.check(TokenKind.STR):
            self.match(TokenKind.STR)
            type_name = 'str'
        elif self.check(TokenKind.LSQUAREBRACKET):
            self.match(TokenKind.LSQUAREBRACKET)
            type_ = self.parse_type()
            self.match(TokenKind.RSQUAREBRACKET)
            return ast.ListType.get(type_)
        else:
            self.error("Unknown type")
        return ast.get_type(type_name)

    def parse_var_def(self) -> Operation:
        """ Parse a variable definition.

        var_def := typed_var `=` literal NEWLINE

        :return: Operation
        """
        typed_var = self.parse_typed_var()
        self.match(TokenKind.ASSIGN)
        literal = self.parse_literal()
        self.match(TokenKind.NEWLINE)
        return ast.VarDef.get(typed_var, literal)

    def parse_global_decl(self) -> Operation:
        """ Parse a global variable declaration.

        global_def := `global` ID NEWLINE

        :return: Operation
        """
        self.match(TokenKind.GLOBAL)
        identifier = self.match(TokenKind.IDENTIFIER)
        self.match(TokenKind.NEWLINE)
        return ast.GlobalDecl.get(identifier.value)

    def parse_nonlocal_decl(self) -> Operation:
        """ Parse a nonlocal variable declaration.

        nonlocal_decl := `nonlocal` ID NEWLINE

        :return: Operation
        """
        self.match(TokenKind.NONLOCAL)
        identifier = self.match(TokenKind.IDENTIFIER)
        self.match(TokenKind.NEWLINE)
        return ast.NonLocalDecl.get(identifier.value)

    def parse_block(self) -> List[Operation]:
        """ Parse a block used in if/while/for statements.

        :return: Region with statements
        """
        self.match(TokenKind.NEWLINE)

        if not self.check(TokenKind.INDENT):
            self.error("expected at least one indented statement in block")

        self.match(TokenKind.INDENT)

        block_region = self.parse_stmt_seq()

        self.match(TokenKind.DEDENT)

        return block_region

    def is_expr_first_set(self) -> bool:
        """
        Check if the next token is in the first set of an expression.

        """
        return (self.check(TokenKind.IDENTIFIER) or self.check(TokenKind.TRUE)
                or self.check(TokenKind.FALSE)
                or self.check(TokenKind.LROUNDBRACKET)
                or self.check(TokenKind.NONE)
                or self.check(TokenKind.IDENTIFIER)
                or self.check(TokenKind.STRING)
                or self.check(TokenKind.INTEGER) or self.check(TokenKind.MINUS)
                or self.check(TokenKind.NOT)
                or self.check(TokenKind.LSQUAREBRACKET))

    def is_stmt_first_set(self) -> bool:
        """
        Check if the next token is in the first set of a statement.

        """
        return (self.is_expr_first_set() or self.check(TokenKind.IF)
                or self.check(TokenKind.WHILE) or self.check(TokenKind.FOR)
                or self.check(TokenKind.PASS) or self.check(TokenKind.RETURN))

    def parse_stmt_seq(self) -> List[Operation]:
        """ Parse a sequence of statements.

        stmt_seq := stmt stmt_seq

        :return: list of Operations
        """
        stmt_seq: List[Operation] = []

        if self.check(TokenKind.ASSIGN):
            self.error('No left-hand side in assign statement')

        while self.is_stmt_first_set():
            stmt_op = self.parse_stmt()
            stmt_seq.append(stmt_op)
            if self.check(TokenKind.INDENT):
                self.error("Unexpected indentation")
            if self.check(TokenKind.ASSIGN):
                self.error('No left-hand side in assign statement')

        return stmt_seq

    def parse_stmt(self) -> Operation:
        """ Parse a statement.

        stmt := simple_stmt NEWLINE
              | if_stmt
              | while_stmt
              | for_stmt
        :return: Statement as operation
        """
        if self.check(TokenKind.IF):
            return self.parse_if_stmt()
        elif self.check(TokenKind.WHILE):
            return self.parse_while_stmt()
        elif self.check(TokenKind.FOR):
            return self.parse_for_stmt()
        simple_stmt = self.parse_simple_stmt()
        self.match(TokenKind.NEWLINE)
        return simple_stmt

    def parse_if_stmt(self) -> Operation:
        """ Parse an if statement from input.

        :return: if operation
        """
        self.match(TokenKind.IF)

        # if condition
        if_cond = self._parse_condition()

        # if body
        if_body = self.parse_block()
        # Now we have, at least, the most basic if statement

        if_blocks = [(if_cond, if_body)]

        while self.check(TokenKind.ELIF):
            self.match(TokenKind.ELIF)
            # elif condition
            elif_cond = self._parse_condition()
            # elif body
            elif_body = self.parse_block()
            if_blocks.append((elif_cond, elif_body))

        else_body = []
        if self.check(TokenKind.ELSE):
            self.match(TokenKind.ELSE)
            self.match(TokenKind.COLON)
            # else body
            else_body = self.parse_block()

        body: List[Operation] = else_body
        if_blocks.reverse()

        if_op = None

        for if_block in if_blocks:
            if_op = ast.If.get(if_block[0], if_block[1], body)
            body = [if_op]

        assert if_op != None, "At least one if-block expected"
        return if_op

    def parse_while_stmt(self) -> Operation:
        """ Parse a while statement from input.

        :return: while operation
        """
        self.match(TokenKind.WHILE)

        # while condition
        while_cond = self._parse_condition()

        # while body
        while_body = self.parse_block()

        while_op = ast.While.get(while_cond, while_body)
        return while_op

    def parse_for_stmt(self) -> Operation:
        """ Parse a for statement from input.

        :return: for operation
        """
        self.match(TokenKind.FOR)

        # iterator
        iter_name = self.match(TokenKind.IDENTIFIER)
        self.match(TokenKind.IN)

        # for expression
        for_expr = self.parse_expr()
        self.match(TokenKind.COLON)

        # for body
        for_body = self.parse_block()
        for_op = ast.For.get(iter_name.value, for_expr, for_body)
        return for_op

    def _parse_condition(self) -> Operation:
        """ Parse an expression as a condition.

        _condition := expr
        Marked as "internal" since it does not belong directly to the parser interface,
        i.e., it does not exist in the grammar specification.
        :return: Operator
        """
        cond = self.parse_expr()
        self.match(TokenKind.COLON)

        return cond

    def parse_simple_stmt(self) -> Operation:
        """ Parse a simple statement.

        stmt := `pass`
              | `return` [expr]?
              | assign_expr
        :return: Statement as operation
        """
        if self.check(TokenKind.PASS):
            self.match(TokenKind.PASS)
            return ast.Pass.get()
        if self.check(TokenKind.RETURN):
            self.match(TokenKind.RETURN)

            if self.is_expr_first_set():
                return ast.Return.get(self.parse_expr())
            else:
                return ast.Return.get(None)

        return self.parse_assign_expr()

    def parse_literal(self) -> Operation:
        """ Parse a literal.

        literal := `None`
                 | `True`
                 | `False`
                 | INTEGER
                 | STRING

        :return: Operation
        """

        # `None`
        if self.check(TokenKind.NONE):
            self.match(TokenKind.NONE)
            return ast.Literal.get(None)

        # `True`
        if self.check(TokenKind.TRUE):
            self.match(TokenKind.TRUE)
            return ast.Literal.get(True)

        # `False`
        if self.check(TokenKind.FALSE):
            self.match(TokenKind.FALSE)
            return ast.Literal.get(False)

        # INTEGER
        if self.check(TokenKind.INTEGER):
            int_token = self.match(TokenKind.INTEGER)
            return ast.Literal.get(int_token.value)

        # STRING
        if self.check(TokenKind.STRING):
            str_token = self.match(TokenKind.STRING)
            return ast.Literal.get(str_token.value)

        self.error('Expected expression')

    def parse_assign_expr(self) -> Operation:
        """
        Parse assign expressions paired with the `=` operator, if such operator exists.
        Otherwise, parse only one expression.

        assign_expr := expr `=` assign_expr
                     | expr

        :return: Operation
        """
        lhs = self.parse_expr()

        if self.check(TokenKind.COLON):
            self.error("Variable declaration after non-declaration statement")

        if self.check(TokenKind.RROUNDBRACKET):
            self.error("unmatched ')'")

        if self.check(TokenKind.ASSIGN):
            self.match(TokenKind.ASSIGN)

            rhs = self.parse_assign_expr()

            lhs = ast.Assign.get(lhs, rhs)

        return lhs

    def parse_expr(self) -> Operation:
        """
        Parse conditional expressions paired with the `if/else` operators, if such operators exists.
        Otherwise, parse only one logical expression.

        expr := or_expr `if` expr `else` expr
              | or_expr

        Conditional expressions are right-associative.
        :return: Operation
        """
        lhs = self.parse_or_expr()

        if self.check(TokenKind.IF):
            self.match(TokenKind.IF)

            cond = self.parse_expr()

            self.match(TokenKind.ELSE)
            rhs = self.parse_expr()

            lhs = ast.IfExpr.get(cond, lhs, rhs)

        return lhs

    def parse_or_expr(self) -> Operation:
        """
        Parse logical expressions paired with the `or` operator, if such an operator exists.
        Otherwise, parse only one logical expression.

        expr := and_expr ('or' and_expr)*

        `or` expressions are left-associative.
        :return: Operation
        """
        lhs = self.parse_and_expr()

        while self.check(TokenKind.OR):
            self.match(TokenKind.OR)

            rhs = self.parse_and_expr()
            lhs = ast.BinaryExpr.get("or", lhs, rhs)

        return lhs

    def parse_and_expr(self) -> Operation:
        """
        Parse logical expressions paired with the `and` operator, if such an operator exists.
        Otherwise, parse only one logical expression.

        and_expr:= not_expr ('and' not_expr)*

        `and` expressions are left-associative.
        :return: Operation
        """
        lhs = self.parse_not_expr()

        while self.check(TokenKind.AND):
            self.match(TokenKind.AND)

            rhs = self.parse_not_expr()
            lhs = ast.BinaryExpr.get("and", lhs, rhs)

        return lhs

    def parse_not_expr(self) -> Operation:
        """
        Parse a logical expression, with optionally a `not` operator.

        not_expr:= 'not' not_expr | arith_expr
        :return: Operation
        """
        if self.check(TokenKind.NOT):
            self.match(TokenKind.NOT)
            not_expr = self.parse_not_expr()
            lhs = ast.UnaryExpr.get("not", not_expr)
        else:
            lhs = self.parse_comp_expr()
        return lhs

    def parse_comp_expr(self) -> Operation:
        """
        Parse a comparison expression.

        comp_expr := arith_expr (comp_op arith_expr)?
          comp_op := `==`
                   | `!=`
                   | `<`
                   | `<=`
                   | `>`
                   | `>=`
                   | `is`

        :return: Operation
        """
        lhs = self.parse_arith_expr()

        if (self.check(TokenKind.EQ) or self.check(TokenKind.NE)
                or self.check(TokenKind.LT) or self.check(TokenKind.LE)
                or self.check(TokenKind.GT) or self.check(TokenKind.GE)
                or self.check(TokenKind.IS)):
            if self.check(TokenKind.EQ):
                op_kind = TokenKind.EQ
            elif self.check(TokenKind.NE):
                op_kind = TokenKind.NE
            elif self.check(TokenKind.LT):
                op_kind = TokenKind.LT
            elif self.check(TokenKind.LE):
                op_kind = TokenKind.LE
            elif self.check(TokenKind.GT):
                op_kind = TokenKind.GT
            elif self.check(TokenKind.GE):
                op_kind = TokenKind.GE
            else:
                op_kind = TokenKind.IS

            op = self.match(op_kind)
            rhs = self.parse_arith_expr()
            lhs = ast.BinaryExpr.get(op.value, lhs, rhs)

            if (self.check(TokenKind.EQ) or self.check(TokenKind.NE)
                    or self.check(TokenKind.LT) or self.check(TokenKind.LE)
                    or self.check(TokenKind.GT) or self.check(TokenKind.GE)
                    or self.check(TokenKind.IS)):
                self.error("Comparison operators are not associative")

        return lhs

    def parse_arith_expr(self) -> Operation:
        """
        Parse an arithmetic expression from input.

        arith_expr := term ((`+` | `-`) cexpr)*

        Arithmetic expressions are left-associative.
        :return: Operation
        """
        lhs = self.parse_term()

        while self.check(TokenKind.PLUS) or self.check(TokenKind.MINUS):
            if self.check(TokenKind.PLUS):
                op_kind = TokenKind.PLUS
            else:
                op_kind = TokenKind.MINUS

            op = self.match(op_kind)
            rhs = self.parse_term()
            lhs = ast.BinaryExpr.get(op.value, lhs, rhs)

        return lhs

    def parse_term(self):
        """
        Parse a term from input.

        term := cexpr ((`*` | `\\` | `%`) cexpr)*

        Terms are left-associative.
        :return: Operation
        """
        lhs = self.parse_cexpr()

        while (self.check(TokenKind.MUL) or self.check(TokenKind.DIV)
               or self.check(TokenKind.MOD)):
            if self.check(TokenKind.MUL):
                op_kind = TokenKind.MUL
            elif self.check(TokenKind.DIV):
                op_kind = TokenKind.DIV
            else:
                op_kind = TokenKind.MOD

            op = self.match(op_kind)
            rhs = self.parse_cexpr()
            lhs = ast.BinaryExpr.get(op.value, lhs, rhs)

        return lhs

    def parse_cexpr(self) -> Operation:
        """ Parse a cexpr from input.

        The rule:

        cexpr := ID
               | ID `(` arglist `)`
               | `(` expr `)`
               | literal
               | cexpr `[` expr `]`

        is converted to:

               cexpr := primary bracket_expr
             primary := ID
                      | ID `(` arglist `)`
                      | `(` expr `)`
                      | literal
        bracket_expr := `[` expr `]` bracket_expr
                      | epsilon

        Parse a primary expression.
        Then, parse optionally a bracket expression and combine it with the primary expression in an index expression.
        For example a[i1][i2] is parsed and returned as: index_expr(index_expr(a, i1), i2)).
        :return: Operation
        """
        primary = self.parse_primary()

        bracket_expr = self.parse_bracket_expr()

        cexpr = primary
        for index in bracket_expr:
            index_expr = ast.IndexExpr.get(cexpr, index)
            cexpr = index_expr

        return cexpr

    def parse_primary(self):
        """
        Parse a primary expression.

        primary := ID
                 | ID `(` arglist `)`
                 | `[` arglist `]`
                 | `(` expr `)`
                 | `-` cexpr
                 | literal

        :return: Operation
        """
        # ID | ID `(` arglist `)`
        if self.check(TokenKind.IDENTIFIER):
            identifier_name = self.match(TokenKind.IDENTIFIER).value
            # ID `(` arglist `)`
            if self.check(TokenKind.LROUNDBRACKET):
                self.match(TokenKind.LROUNDBRACKET)
                arglist = self.parse_arglist()

                if self.is_expr_first_set():
                    self.error("expression found, but comma expected")

                self.match(TokenKind.RROUNDBRACKET)

                return ast.CallExpr.get(identifier_name, arglist)
            # ID
            else:
                return ast.ExprName.get(identifier_name)

        # `[' arglist `]`
        if self.check(TokenKind.LSQUAREBRACKET):
            self.match(TokenKind.LSQUAREBRACKET)
            arglist = self.parse_arglist()

            if self.is_expr_first_set():
                self.error("expression found, but comma expected")

            self.match(TokenKind.RSQUAREBRACKET)

            return ast.ListExpr.get(arglist)

        # `(` expr `)`
        if self.check(TokenKind.LROUNDBRACKET):
            self.match(TokenKind.LROUNDBRACKET)
            cexpr = self.parse_expr()
            self.match(TokenKind.RROUNDBRACKET)
            return cexpr

        # `-` cexpr
        if self.check(TokenKind.MINUS):
            self.match(TokenKind.MINUS)
            cexpr = self.parse_cexpr()
            return ast.UnaryExpr.get('-', cexpr)

        # literal
        return self.parse_literal()

    def parse_arglist(self) -> List[Operation]:
        """
        Parse an (empty) list of function call arguments.

        arglist := expr argrep
                   | epsilon
        :return: The list of arguments as Operations
        """

        # expr argrep
        if self.is_expr_first_set():
            expr = self.parse_expr()
            expr_list_tail = self.parse_argrep()
            return [expr] + expr_list_tail

        # epsilon
        return []

    def parse_argrep(self) -> List[Operation]:
        """
        Parse the tail of a list of expression.

        argrep := `,` expr argrep
                  | epsilon
        :return: A (empty) list of expressions
        """

        # `,` expr argrep
        if self.check(TokenKind.COMMA):
            self.match(TokenKind.COMMA)
            expr = self.parse_expr()
            argrep = self.parse_argrep()
            return [expr] + argrep

        # epsilon
        return []

    def parse_bracket_expr(self) -> List[Operation]:
        """
        Parse a bracket expression, if it exists.

        bracket_expr := `[` expr `]` bracket_expr
                      | epsilon

        For example, a[i1][i2] is parsed sequentially and a list with the parsed indices [i1, i2] is returned.
        :return: a list of the indices of the bracket expression as Operations, if they exist, otherwise an empty list.
        """
        bracket_expr: List[Operation] = []
        while self.check(TokenKind.LSQUAREBRACKET):
            self.match(TokenKind.LSQUAREBRACKET)
            index = self.parse_expr()
            self.match(TokenKind.RSQUAREBRACKET)
            bracket_expr.append(index)
        return bracket_expr

WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
from io import TextIOBase, IOBase
from enum import Enum, auto
from dataclasses import dataclass

from typing import Any, List, Union, Optional


class TokenKind(Enum):
    EOF = auto()

    # Newline
    NEWLINE = auto()

    # Indentation
    INDENT = auto()
    DEDENT = auto()

    # Commands
    CLASS = auto()
    DEF = auto()
    GLOBAL = auto()
    NONLOCAL = auto()
    PASS = auto()
    RETURN = auto()

    # Primary
    IDENTIFIER = auto()
    INTEGER = auto()
    STRING = auto()

    # Control-flow
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()

    # Symbols
    PLUS = auto()
    MINUS = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    ASSIGN = auto()
    LROUNDBRACKET = auto()
    RROUNDBRACKET = auto()
    COLON = auto()
    LSQUAREBRACKET = auto()
    RSQUAREBRACKET = auto()
    COMMA = auto()
    RARROW = auto()

    # Comparison Operators
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    IS = auto()

    # VALUES
    NONE = auto()
    TRUE = auto()
    FALSE = auto()

    # Logical operators
    OR = auto()
    AND = auto()
    NOT = auto()

    # TYPES
    OBJECT = auto()
    INT = auto()
    BOOL = auto()
    STR = auto()


@dataclass
class Token:
    kind: TokenKind
    value: Any = None
    column: int = -1

    def __repr__(self) -> str:
        if self.value is None and self.column < 0:
            return self.kind.name
        elif self.value is None:
            return self.kind.name + ":" + str(self.column)
        elif self.kind is TokenKind.STRING:
            # Get the string with escaped characters.
            str2 = self.value.replace("\\", "\\\\") \
                .replace("\t", "\\t") \
                .replace("\r", "\\r") \
                .replace("\n", "\\n") \
                .replace("\"", "\\\"")
            return self.kind.name + ":" + str2 + "," + str(self.column)
        else:
            return self.kind.name + ":" + str(self.value) + "," + str(
                self.column)


class Scanner:

    def __init__(self, stream: TextIOBase):
        """ Create a new scanner.

        The scanner's input is a stream derived from a string or a file.

        # Lexing a string
        s = io.StringIO("1 + 2")
        Scanner(s)

        # Lexing a file
        s = open("file.choc")
        Scanner(s)

        :param stream: The stream of characters to be lexed.
        """
        self.stream: TextIOBase = stream
        self.buffer: Optional[str] = None  # A buffer of one character.
        self.column: int = -1  # The "tip" of the scanner, i.e. how far inside the line_buffer are we.
        self.line_buffer: str = ''

    def peek(self) -> str:
        """ Return the next character from input without consuming it.

        :return: The next character in the input stream or None at the end of the stream.
        """
        # A buffer of one character is used to store the last scanned character.
        # If the buffer is empty, it is filled with the next character from the input.
        if not self.buffer:
            self.buffer = self.consume()
        return self.buffer

    def consume(self):
        """ Consume and return the next character from input.

        :return: The next character in the input stream or None at the end of the stream.
        """
        # If the buffer is full, we empty the buffer and return the character it contains.
        if self.buffer:
            c = self.buffer
            self.buffer = None
            return c
        c = self.stream.read(1)
        self.column += 1
        self.line_buffer += c
        return c


class Tokenizer:

    def __init__(self, scanner: Scanner):
        self.scanner = scanner
        self.buffer: List[Token] = []  # A buffer of tokens
        self.line_number = 0
        self.is_new_line = True
        self.is_logical_line = False
        self.line_indent_lvl = 0  # How "far" we are inside the line, i.e. what column.
        # Resets after every end-of-line sequence.
        self.indent_stack = [0]

    def peek(self, k: int = 1) -> Union[Token, List[Token]]:
        """ Peeks through the next `k` number of tokens.

        This functions looks ahead the next `k` number of tokens,
        and returns them as a list.
        It uses a FIFO buffer to store tokens temporarily.
        :param k: number of tokens
        :return: one token or a list of tokens
        """
        if not self.buffer:
            self.buffer = [self.consume()]

        # Fill the buffer up to `k` tokens, if needed.
        buffer_size = len(self.buffer)
        if buffer_size < k:
            for _ in list(range(k - buffer_size)):
                self.buffer.append(self.consume(keep_buffer=True))

        # If you need only one token, return it as an element,
        # not as a list with one element.
        if k == 1:
            return self.buffer[0]

        return self.buffer[0:k]

    def consume(self, keep_buffer: bool = False) -> Token:
        """ Consumes one token and implements peeking through the next one.

        If we want to only peek and not consume, we set the `keep_buffer` flag.
        This argument is passed to additional calls to `next`.
        The idea is that we can peek through more than one tokens (by keeping them in the buffer),
        but we consume tokens only one by one.
        :param keep_buffer: whether to keep the buffer intact, or consume a token from it
        :return: one token
        """
        if self.buffer and not keep_buffer:
            c = self.buffer[0]
            self.buffer = self.buffer[1:]
            return c

        # If we just switched line, flush the buffer.
        if self.is_new_line and not self.is_logical_line:
            self.scanner.line_buffer = ''

        c = self.scanner.peek()

        while True:
            col = self.scanner.column
            if c.isspace():
                # Tabs are replaced from left to right by one to eight spaces.
                # The total number of spaces up to and including the replacement should be a multiple of eight.
                if c == '\t':
                    if self.is_new_line:  # We only care about padding at the beginning of line.
                        self.line_indent_lvl += 8 - self.line_indent_lvl % 8
                        self.scanner.column += 8 - self.scanner.column % 8
                elif c == '\n':  # line feed handling
                    self.line_indent_lvl = 0
                    self.is_new_line = True
                    self.line_number += 1
                    self.scanner.column = -1
                    if self.is_logical_line:
                        self.is_logical_line = False
                        self.scanner.consume()
                        return Token(TokenKind.NEWLINE, None, col)
                elif c == '\r':  # carriage return handling
                    self.line_indent_lvl = 0
                    self.is_new_line = True
                    self.line_number += 1
                    self.scanner.column = -1
                    if self.is_logical_line:
                        self.is_logical_line = False
                        self.scanner.consume()
                        return Token(TokenKind.NEWLINE, None, col)
                else:  # Handle the rest whitespaces
                    if self.is_new_line:
                        self.line_indent_lvl += 1
                # Consume whitespace
                self.scanner.consume()
                return self.consume(keep_buffer)
            # One line comments
            # get_char() returns None in the case of EOF.
            elif c == '#':
                self.scanner.consume()
                c = self.scanner.peek()
                while c and c != '\n' and c != '\r':
                    self.scanner.consume()
                    c = self.scanner.peek()
                self.scanner.line_buffer = ''
                continue
            # Indentation
            elif c and not c.isspace() and c != '#' and self.is_new_line:
                # OK, we are in a logical line now (at least one token that is not whitespace or comment).
                self.is_logical_line = True
                if self.line_indent_lvl > self.indent_stack[
                        -1]:  # New indentation level
                    # Push the indentation level to the stack.
                    self.indent_stack.append(self.line_indent_lvl)
                    # Indent token's position starts on the previous indentation level's column.
                    col = self.indent_stack[-2]
                    # Return indent token.
                    # Do not consume any character (this will happen in the next call of get_token()).
                    return Token(TokenKind.INDENT, None, col)
                elif self.line_indent_lvl < self.indent_stack[
                        -1]:  # Previous indentation level is (probably) closing.
                    try:
                        self.indent_stack.index(self.line_indent_lvl)
                        # Pop the last of the indentation levels that are higher.
                        self.indent_stack = self.indent_stack[0:-1]
                        # Dedent token's position starts on the current indentation level's column.
                        col = self.indent_stack[-1]
                        # Return dedent token.
                        # Do not consume any character (this will happen in a next call of get_token()).
                        return Token(TokenKind.DEDENT, None, col)
                    except ValueError:
                        print('Indentation error: mismatched blocks.')
                        exit(1)
                # Since we were flushing the buffer until we found a non whitespace character,
                # we need to add to the buffer the indentation spaces that we have skipped.
                self.scanner.line_buffer = self.line_indent_lvl * ' ' + self.scanner.line_buffer
                self.is_new_line = False
            elif c == '+':
                self.scanner.consume()
                return Token(TokenKind.PLUS, '+', col)
            elif c == '-':
                self.scanner.consume()
                c += self.scanner.peek()
                if c == '->':
                    self.scanner.consume()
                    return Token(TokenKind.RARROW, '->', col)
                else:
                    return Token(TokenKind.MINUS, '-', col)
            elif c == '*':
                self.scanner.consume()
                return Token(TokenKind.MUL, '*', col)
            elif c == '%':
                self.scanner.consume()
                return Token(TokenKind.MOD, '%', col)
            elif c == '/':
                self.scanner.consume()
                c += self.scanner.peek()
                if c == '//':
                    self.scanner.consume()
                    return Token(TokenKind.DIV, '//', col)
                else:
                    raise Exception('Unknown lexeme: {}'.format(c))
            elif c == '=':
                self.scanner.consume()
                c += self.scanner.peek()
                if c == '==':
                    self.scanner.consume()
                    return Token(TokenKind.EQ, '==', col)
                else:
                    return Token(TokenKind.ASSIGN, '=', col)
            elif c == '!':
                self.scanner.consume()
                c += self.scanner.peek()
                if c == '!=':
                    self.scanner.consume()
                    return Token(TokenKind.NE, '!=', col)
                else:
                    raise Exception('Unknown lexeme: {}'.format(c))
            elif c == '<':
                self.scanner.consume()
                c += self.scanner.peek()
                if c == '<=':
                    self.scanner.consume()
                    return Token(TokenKind.LE, '<=', col)
                else:
                    return Token(TokenKind.LT, '<', col)
            elif c == '>':
                self.scanner.consume()
                c += self.scanner.peek()
                if c == '>=':
                    self.scanner.consume()
                    return Token(TokenKind.GE, '>=', col)
                else:
                    return Token(TokenKind.GT, '>', col)
            elif c == '(':
                self.scanner.consume()
                return Token(TokenKind.LROUNDBRACKET, '(', col)
            elif c == ')':
                self.scanner.consume()
                return Token(TokenKind.RROUNDBRACKET, ')', col)
            elif c == ':':
                self.scanner.consume()
                return Token(TokenKind.COLON, ':', col)
            elif c == '[':
                self.scanner.consume()
                return Token(TokenKind.LSQUAREBRACKET, '[', col)
            elif c == ']':
                self.scanner.consume()
                return Token(TokenKind.RSQUAREBRACKET, ']', col)
            elif c == ',':
                self.scanner.consume()
                return Token(TokenKind.COMMA, ',', col)
            # Identifier: [a-zA-Z_][a-zA-Z0-9_]*
            elif c.isalpha() or c == '_':
                name = self.scanner.consume()
                c = self.scanner.peek()
                while c.isalnum() or c == '_':
                    name += self.scanner.consume()
                    c = self.scanner.peek()

                if name == 'class':
                    return Token(TokenKind.CLASS, 'class', col)
                if name == 'def':
                    return Token(TokenKind.DEF, 'def', col)
                if name == 'global':
                    return Token(TokenKind.GLOBAL, 'global', col)
                if name == 'nonlocal':
                    return Token(TokenKind.NONLOCAL, 'nonlocal', col)
                if name == 'if':
                    return Token(TokenKind.IF, 'if', col)
                if name == 'elif':
                    return Token(TokenKind.ELIF, 'elif', col)
                if name == 'else':
                    return Token(TokenKind.ELSE, 'else', col)
                if name == 'while':
                    return Token(TokenKind.WHILE, 'while', col)
                if name == 'for':
                    return Token(TokenKind.FOR, 'for', col)
                if name == 'in':
                    return Token(TokenKind.IN, 'in', col)
                if name == 'None':
                    return Token(TokenKind.NONE, 'None', col)
                if name == 'True':
                    return Token(TokenKind.TRUE, 'True', col)
                if name == 'False':
                    return Token(TokenKind.FALSE, 'False', col)
                if name == 'pass':
                    return Token(TokenKind.PASS, 'pass', col)
                if name == 'or':
                    return Token(TokenKind.OR, 'or', col)
                if name == 'and':
                    return Token(TokenKind.AND, 'and', col)
                if name == 'not':
                    return Token(TokenKind.NOT, 'not', col)
                if name == 'is':
                    return Token(TokenKind.IS, 'is', col)
                if name == 'object':
                    return Token(TokenKind.OBJECT, 'object', col)
                if name == 'int':
                    return Token(TokenKind.INT, 'int', col)
                if name == 'bool':
                    return Token(TokenKind.BOOL, 'bool', col)
                if name == 'str':
                    return Token(TokenKind.STR, 'str', col)
                if name == 'return':
                    return Token(TokenKind.RETURN, 'return', col)

                return Token(TokenKind.IDENTIFIER, name, col)
            # Number: [0-9]+
            elif c.isdigit():
                value = self.scanner.consume()
                while self.scanner.peek().isnumeric():
                    value += self.scanner.consume()
                return Token(TokenKind.INTEGER, int(value), col)
            # String
            elif c == '"':
                string: str = ''
                self.scanner.consume()
                c = self.scanner.peek()
                while c != '"':
                    if 32 <= ord(c) <= 126:  # ASCII limits accepted
                        if c != '\\':
                            string += self.scanner.consume()
                        # Handle escape characters
                        else:
                            self.scanner.consume()  # Consume '\\'
                            c = self.scanner.peek()
                            if c == 'n':
                                string += '\n'
                            elif c == 't':
                                string += '\t'
                            elif c == '"':
                                string += '"'
                            elif c == '\\':
                                string += '\\'
                            else:
                                print('Error: "\\{}" not recognized'.format(c))
                                exit(1)
                            self.scanner.consume()  # Consume escaped character
                    else:
                        print('Error: Unknown ASCII number {}'.format(ord(c)))
                        exit(1)
                    c = self.scanner.peek()
                self.scanner.consume()
                return Token(TokenKind.STRING, string, col)
            # End of file
            elif not c:
                # The end of input also serves as an implicit terminator of the physical line.
                # For a logical line emit a newline token.
                if self.is_logical_line:
                    self.is_logical_line = False
                    return Token(TokenKind.NEWLINE, None, col)
                if self.indent_stack[
                        -1] > 0:  # A dedent token is generated for the rest non-zero numbers on the stack.
                    self.indent_stack = self.indent_stack[0:-1]
                    # Dedent token's position starts on the current indentation level's column.
                    col = self.indent_stack[-1]
                    return Token(TokenKind.DEDENT, None, col)
                return Token(TokenKind.EOF, None, col)
            else:
                raise Exception("Invalid character detected: '" + c + "'")


class Lexer:

    def __init__(self, stream: TextIOBase):
        scanner = Scanner(stream)
        self.tokenizer = Tokenizer(scanner)

    def peek(self, k: int = 1) -> Union[Token, List[Token]]:
        return self.tokenizer.peek(k)

    def consume(self) -> Token:
        return self.tokenizer.consume()

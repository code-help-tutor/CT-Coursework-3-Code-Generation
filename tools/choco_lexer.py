WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
#!/usr/bin/env python3

import argparse
from choco.lexer import Lexer, TokenKind


def __main__():
    parser = argparse.ArgumentParser(description='A ChocoPy lexer')
    parser.add_argument('file', type=argparse.FileType('r'))
    args = parser.parse_args()

    lexer = Lexer(args.file)
    while True:
        token = lexer.consume()
        print(token)
        if token.kind == TokenKind.EOF:
            break


if __name__ == "__main__":
    __main__()

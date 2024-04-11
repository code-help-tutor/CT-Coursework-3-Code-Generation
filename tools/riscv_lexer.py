WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
#!/usr/bin/env python3

import argparse

from riscv.lexer import Lexer


def __main__():
    parser = argparse.ArgumentParser(description='A RISC-V lexer')
    parser.add_argument('file', type=argparse.FileType('r'))
    args = parser.parse_args()

    lexer = Lexer(args.file)
    while True:
        token = lexer.next()
        if not token:
            break
        print(token)


if __name__ == "__main__":
    __main__()

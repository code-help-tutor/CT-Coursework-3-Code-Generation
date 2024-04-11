WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
# RUN: ../../../riscv/parser.py %s | filecheck %s

.asciz "somestring"
# CHECK: .asciz "somestring"

.section .text
# CHECK: .section .text

.global getasm
# CHECK: .global getasm


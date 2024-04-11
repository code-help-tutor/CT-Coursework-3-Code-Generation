WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
# RUN: riscv-lexer %s | filecheck %s

.asciz "somestring"
# CHECK: DOT
# CHECK-NEXT: SYMBOL:asciz
# CHECK-NEXT: LITERAL:"somestring"
# CHECK-NEXT: NEWLINE

.section .text
# CHECK: DOT
# CHECK-NEXT: SYMBOL:section
# CHECK-NEXT: DOT
# CHECK-NEXT: SYMBOL:text
# CHECK-NEXT: NEWLINE

.global getasm
# CHECK: DOT
# CHECK-NEXT: SYMBOL:global
# CHECK-NEXT: SYMBOL:getasm


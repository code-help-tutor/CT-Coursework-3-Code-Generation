WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
# RUN: ../../../riscv/parser.py %s | filecheck %s

foo:
	add a0, a0, a0

# CHECK: foo:
# CHECK-NEXT: add a0, a0, a0

bar:
	add a0, a0, a0

# CHECK: bar:
# CHECK-NEXT: add a0, a0, a0

WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
# RUN: riscv-interpreter %s | filecheck %s

; hello-world.asm
; print "Hello World" to stdout and exit
        .data
msg:    .ascii "Hello World!\n"
        .text
        addi    a0, zero, 1             ; print to stdout
        addi    a1, zero, msg           ; load msg address
        addi    a2, zero, 12            ; write 12 bytes
        addi    a7, zero, SCALL_WRITE   ; write syscall code
        ecall
        addi    a0, zero, 0             ; set exit code to 0
        addi    a7, zero, SCALL_EXIT    ; exit syscall code
        ecall

; CHECK: Hello World!
; CHECK-NEXT: Return code: 0

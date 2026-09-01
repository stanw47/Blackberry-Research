
.section .text.start
.thumb
.global _start
_start:
	LDR R0, =0x107280
	MOV SP, R0

	BL stage2_main

	LDR R0, =0x15F3
	BX R0


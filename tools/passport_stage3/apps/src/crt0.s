
.section .text.start
.arm
.global _start
_start:
	LDR R0, =0xFC10723C
	MOV R1, #0x15C9
	STR R1, [R0]

	LDR             R0, =0xFC102080
	MSR             CPSR_c, #0xD3
	MOV             SP, R0
	MSR             CPSR_c, #0xDB
	MOV             SP, R0
	MSR             CPSR_c, #0xD7
	MOV             SP, R0
	MSR             CPSR_c, #0xD3

	MOV             R4, #0
	MOV             R5, #0
	MOV             R6, #0
	MOV             R7, #0
	MOV             R8, #0
	MOV             R9, #0
	MOV             R10, #0
	MOV             R11, #0
	MOV             R12, #0

	LDR             PC, =stage2_main

.global memcpy
memcpy:
	LDR PC, =0xFC010984

.global memset
memset:
	LDR PC, =0xFC01D0A0

.global memzero
memzero:
	LDR PC, =0xFC010A08

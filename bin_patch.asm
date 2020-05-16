.psx

.open "data/repack/SCPS_100.23",0x8000F800
.org 0x80016b54
.area 0x34C
  ;ASCII to SJIS lookup table
  SJIS_LOOKUP:
  .sjisn "　！”＃＄％＆"
  ;Fix ' since it doesn't get encoded correctly
  db 0x81 :: db 0x66
  ;Also change + to * and _ to ;
  .sjisn "（）＋＋，－．／０１２３４５６７８９：＿〈＝〉？＠"
  .sjisn "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿　"
  .sjisn "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｝｜～"

  ;VWF lookup table
  VWF_LOOKUP:
  .import "data/vwf.bin"
  .align

  ;t5 = temp
  ;t9 = $c check
  ;a0 = char
  ;a1 = source pointer
  ;s0 = dest pointer
  ASCII_FUNC:
  ;Copy both bytes for sjis characters
  li t5,0x79
  bgt a0,t5,ASCII_SJIS
  ;0x1f: the string was redirected to another location
  li t5,0x1f
  beq a0,t5,ASCII_REDIRECT
  ;If < 0x21, just copy the byte
  li t5,0x21
  blt a0,t5,ASCII_COPY
  ;Handle @
  li t5,0x40
  beq a0,t5,ASCII_COPY
  ;Handle char codes that start with $
  li t5,0x24
  beq a0,t5,ASCII_CCODES
  ;Check t9 to figure out if we need to add a $c
  li t5,0x1
  beq t5,t9,ASCII_CHECKC_DONE
  move t9,t5
  li t5,0x24
  sb t5,0x0(s0)
  li t5,0x63
  sb t5,0x1(s0)
  addiu s0,s0,0x2
  ASCII_CHECKC_DONE:
  ;Convert the ASCII character to SJIS using the lookup table
  li t5,SJIS_LOOKUP
  addiu a0,a0,-0x20
  sll a0,a0,0x1
  addu a0,a0,t5
  lbu t5,0x0(a0)
  lbu a0,0x1(a0)
  sb t5,0x0(s0)
  sb a0,0x1(s0)
  addiu s0,s0,0x2
  addiu a1,a1,0x1
  jr ra :: nop
  ;Copy 2 bytes for SJIS
  ASCII_SJIS:
  lbu t5,0x1(a1)
  sb a0,0x0(s0)
  sb t5,0x1(s0)
  addiu a1,a1,0x2
  addiu s0,s0,0x2
  jr ra :: nop
  ;Copy 2 bytes for control codes
  ASCII_CCODES:
  lbu t5,0x1(a1)
  sb a0,0x0(s0)
  sb t5,0x1(s0)
  addiu a1,a1,0x2
  addiu s0,s0,0x2
  ;Check for $g code
  li a0,0x67
  bne a0,t5,ASCII_CCODES_DONE
  ;For $g codes, keep copying until it finds numbers
  ASCII_CCODES_G:
  lbu t5,0x0(a1)
  li a0,0x3a
  addiu t5,t5,-0x2f
  bge t5,a0,ASCII_CCODES_DONE
  lbu t5,0x0(a1)
  addiu a1,a1,0x1
  sb t5,0x0(s0)
  addiu s0,s0,0x1
  j ASCII_CCODES_G :: nop
  ASCII_CCODES_DONE:
  jr ra :: nop
  ;Just copy the character
  ASCII_COPY:
  sb a0,0x0(s0)
  addiu a1,a1,0x1
  addiu s0,s0,0x1
  jr ra
  ;Add the new address to the source and return
  ASCII_REDIRECT:
  lbu t5,0x2(a1)
  lbu a0,0x1(a1)
  sll t5,t5,0x8
  or t5,t5,a0
  addu a1,a1,t5
  jr ra :: nop

  ASCII:
  ;Return to normal execution to handle %
  beq v1,v0,ASCII_PERC
  ;Call the function
  move a0,v1
  move a1,s1
  jal ASCII_FUNC :: nop
  j ASCII_RETURN
  move s1,a1
  ASCII_PERC:
  j ASCII_RETURN_PERC :: nop

  ASCII_SPRINTF:
  ;Call the function
  move a0,v0
  move a1,v1
  jal ASCII_FUNC :: nop
  move v1,a1
  j ASCII_SPRINTF_RETURN :: nop

  ;s1 = character
  ;r20 = spacing
  VWF:
  ;Skip japanese characters
  li t1,0x60
  li t2,VWF_LOOKUP
  bge s1,t1,VWF_JAP
  ;Get the VWF width from the lookup table
  addu t2,t2,s1
  lbu t1,0x0(t2)
  ;Check if > 0x10
  li t2,0x10
  bgt t1,t2,VWF_ALIGN :: nop
  j VWF_RETURN
  addu s4,s4,t1
  ;Set the X position (*2) instead of adding to it
  VWF_ALIGN:
  sll t1,t1,0x1
  j VWF_RETURN
  move s4,t1
  ;Default to 0x8 for japanese characters
  VWF_JAP:
  addiu s4,s4,0x8
  j VWF_RETURN :: nop

  ;Check if there are 2 consecutive 0s and move to the next line
  VWF_FIX:
  lbu s1,0x38(v0)
  lbu v0,0x39(v0) :: nop
  addu v0,s1,v0
  bgt v0,zero,VWF_FIX_NOTZERO :: nop
  j VWF_FIX_ENDLINE
  li v0,0x20
  VWF_FIX_NOTZERO:
  j VWF_FIX_RETURN
  li v0,0x20

  CONTROLLER:
  ;Swap bits 5 and 6 in a0 (controller buffer read from memory)
  srl t0,a0,0x5
  srl t1,a0,0x6
  xor t0,t0,t1
  andi t0,t0,0x1
  sll t1,t0,0x5
  sll t0,t0,0x6
  or t0,t0,t1
  xor a0,a0,t0
  ;Original code
  sll v1,v1,0x8
  nor v1,v1,a0
  j CONTROLLER_RETURN :: nop
.endarea

;Reset t9 which we use to add a $c if we encounter ASCII
.org 0x800777cc
  move t9,zero
;Hook the function that copies the string in memory
.org 0x800777dc
  j ASCII
  clear a1
  ASCII_RETURN_PERC:
;Return here when we're done
.org 0x800779d0
  ASCII_RETURN:
;Hook the function that copies the sprintf parameter
.org 0x80077944
  j ASCII_SPRINTF :: nop
  ASCII_SPRINTF_RETURN:
;Don't increase s0 here
.org 0x80077958
  nop

;Replace the fixed with for half characters
.org 0x8007bae4
  j VWF
  addiu s8,s8,0x1
  VWF_RETURN:
;Fix overdraw that isn't normally visible
.org 0x8007b630
  j VWF_FIX
  nop
  VWF_FIX_RETURN:
.org 0x8007bb0c
  VWF_FIX_ENDLINE:
;Increase the maximum line length
.org 0x80077eac
  li v1,0x14

;Swap Circle and Cross
.org 0x80057010
  j CONTROLLER :: nop
  CONTROLLER_RETURN:

;Enable debug mode
.ifdef DEBUG
.org 0x80056354
  sh t5,0x4054(at)
.endif

.close

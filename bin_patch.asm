.psx

.open "data/repack/SCPS_100.23",0x8000F800
.org 0x80016b54
  ;ASCII to SJIS lookup table
  SJIS_LOOKUP:
  .sjisn "　！゛＃＄％＆｀（）＊＋，－．／０１２３４５６７８９：；〈＝〉？＠"
  .sjisn "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿｀"
  .sjisn "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｝｜～"
  .align

  ;Check t9 to figure out if we need to add a $c
  .macro CheckC,val
    li t5,val
    beq t5,t9,CHECKC_DONE
    move t9,t5
    li t5,0x24
    sb t5,0x0(s0)
    li t5,0x63
    sb t5,0x1(s0)
    addiu s0,s0,0x2
    CHECKC_DONE:
  .endmacro

  ;t5 = temp
  ;t9 = $c check
  ;a0 = char
  ;a1 = source pointer
  ;s0 = dest pointer
  ASCII_FUNC:
  ;Copy both bytes for sjis characters
  li t5,0x79
  bgt a0,t5,ASCII_SJIS
  ;If < 0x21, just copy the byte
  li t5,0x21
  blt a0,t5,ASCII_COPY
  ;Handle @
  li t5,0x40
  beq a0,t5,ASCII_COPY
  ;Handle char codes that start with $
  li t5,0x24
  beq a0,t5,ASCII_CCODES
  ;Convert the ASCII character to SJIS using the lookup table
  CheckC 0x1
  li t5,SJIS_LOOKUP
  addiu a0,a0,-0x20
  sll a0,a0,0x1
  addu a0,a0,t5
  lbu t5,0x0(a0) :: nop
  sb t5,0x0(s0)
  lbu t5,0x1(a0) :: nop
  sb t5,0x1(s0)
  addiu s0,s0,0x2
  addiu a1,a1,0x1
  jr ra :: nop
  ;Copy 2 bytes for SJIS and control codes, and reset t9 for SJIS
  ASCII_SJIS:
  CheckC 0x0
  ASCII_CCODES:
  lbu t5,0x1(a1)
  sb a0,0x0(s0)
  sb t5,0x1(s0)
  addiu a1,a1,0x2
  addiu s0,s0,0x2
  jr ra :: nop
  ;Just copy some characters
  ASCII_COPY:
  sb a0,0x0(s0)
  addiu a1,a1,0x1
  addiu s0,s0,0x1
  jr ra :: nop

  ASCII:
  ;Return to normal execution to handle %
  beq v1,v0,ASCII_PERC
  ;Call the function
  move a0,v1
  move a1,s1
  jal ASCII_FUNC :: nop
  move s1,a1
  j ASCII_RETURN :: nop
  ASCII_PERC:
  j ASCII_RETURN_PERC :: nop

  ASCII_SPRINTF:
  ;Call the function
  move a0,v0
  move a1,v1
  jal ASCII_FUNC :: nop
  move v1,a1
  j ASCII_SPRINTF_RETURN :: nop

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

.close

.psx

;Libary functions
ClearImage   equ 0x8009d0fc
LoadImage    equ 0x8009d190
MoveImage    equ 0x8009d258
DrawSync     equ 0x8009cf68
strlen       equ 0x8009b920
;Other locations/values
DebugEnabled equ 0x800f4054
FontTable    equ 0x800c49cc
FontVRamX    equ 1024 - (256 / 4)
FontVRamY    equ 48

.open "data/repack/SCPS_100.23",0x8000F800

;Replace the anime text rendering function
.org 0x80048f24
.area 0x2C0
  ;ASCII to SJIS lookup table
  SJIS_LOOKUP:
  .sjisn "　！”＃＄％＆"
  ;Fix ' since it doesn't get encoded correctly
  db 0x81 :: db 0x66
  ;Also change + to * and _ to ;
  .sjisn "（）＋＋，－．／０１２３４５６７８９：＿〈＝〉？＠"
  .sjisn "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿　"
  .sjisn "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｝｜～"
  .align

  ;VWF lookup table
  VWF_LOOKUP:
  .import "data/vwf.bin"
  .definelabel VWF_LOOKUP2,VWF_LOOKUP + 0x60
  .align

  ;Character rendering function
  ;a0 = ASCII character
  ;a1 = x position
  ;a2 = y position
  CharRender:
  ;Setup stack
  addiu sp,sp,-0x20
  sw ra,0x0(sp)
  ;Check if it's a space
  li v0,0x20
  bne a0,v0,CHAR_RENDER_NOSPACE
  ;Return the space VWF value
  CHAR_RENDER_SPACE:
  li v0,VWF_LOOKUP2
  li a0,0x20
  addu v0,v0,a0
  j CHAR_RENDER_RETURN
  lbu t9,0x0(v0)
  CHAR_RENDER_NOSPACE:
  ;ASCII to SJIS
  li v0,SJIS_LOOKUP
  addiu a0,a0,-0x20
  sll a0,a0,0x1
  addu a0,a0,v0
  lbu v0,0x0(a0)
  lbu a0,0x1(a0)
  ;Get character index in font
  ;Loop the font table from the game, the format is:
  ;xx xx 00 yy 00 (x = sjis, y = index)
  li t0,FontTable-0x5
  li v1,0x100
  CHAR_RENDER_FONT:
  addiu t0,t0,0x5
  addiu v1,v1,-0x1
  ;If 0x100 is reached, just render a space
  beq v1,zero,CHAR_RENDER_SPACE
  lbu t1,0x0(t0) :: nop
  bne v0,t1,CHAR_RENDER_FONT
  lbu t1,0x1(t0) :: nop
  bne a0,t1,CHAR_RENDER_FONT :: nop
  lbu a0,0x3(t0)
  ;Get VWF value
  li t0,VWF_LOOKUP2
  addu t0,t0,a0
  lbu t9,0x0(t0)
  ;Font index (a0) to VRAM x,y (t0,t1)
  li v0,0x20
  divu a0,v0
  mfhi t0
  sll t0,t0,0x1
  mflo t1
  sll t1,t1,0x4
  addiu t0,t0,FontVRamX
  addiu t1,t1,FontVRamY
  ;Set MoveImage source_rect (x, y, w, h)
  addiu a0,sp,0x10
  sh t0,0x10(sp)
  sh t1,0x12(sp)
  li v0,0x2
  sh v0,0x14(sp)
  li v0,0x10
  sh v0,0x16(sp)
  ;MoveImage(*source_rect, dest_x, dest_y)
  jal MoveImage
  sh v0,0x1e(sp)
  CHAR_RENDER_RETURN:
  lw ra,0x0(sp)
  addiu sp,sp,0x20
  jr ra
  move v0,t9
.endarea

;Replace error codes
.org 0x80016b54
.area 0x34C
  ;Copy a character from a string to a buffer, converting it to SJIS if ASCII
  ;Also handles various control codes found in string
  ;t5 = temp
  ;a0 = char
  ;a1 = source pointer
  ;s0 = dest pointer
  CopyASCII:
  ;Copy both bytes for sjis characters
  li t5,0x7f
  bgt a0,t5,ASCII_SJIS
  ;0x1f: the string was redirected to another location
  li t5,0x1f
  beq a0,t5,ASCII_REDIRECT
  ;0x1e: insert $c
  li t5,0x1e
  beq a0,t5,ASCII_INSERTC
  ;If < 0x20, just copy the byte
  li t5,0x20
  blt a0,t5,ASCII_COPY
  ;Handle space
  li t5,0x20
  beq a0,t5,ASCII_SPACE
  ;Handle @
  li t5,0x40
  beq a0,t5,ASCII_COPY
  ;Handle char codes that start with $
  li t5,0x24
  beq a0,t5,ASCII_CCODES
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
  jr ra
  ;Convert space to SJIS
  ASCII_SPACE:
  li t5,0x81
  li a0,0x40
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
  jr ra
  ;Insert $c
  ASCII_INSERTC:
  li t5,0x24
  sb t5,0x0(s0)
  li t5,0x63
  sb t5,0x1(s0)
  addiu a1,a1,0x1
  addiu s0,s0,0x2
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
  jal CopyASCII
  move a1,s1
  j ASCII_RETURN
  move s1,a1
  ASCII_PERC:
  j ASCII_RETURN_PERC :: nop

  ASCII_SPRINTF:
  ;Call the function
  move a0,v0
  jal CopyASCII
  move a1,v1
  j ASCII_SPRINTF_RETURN
  move v1,a1

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

  ;Moved some anime code here to fit the limited space
  ANIME_RENDER_CODE:
  andi a1,s2,0xffff
  srl a1,a1,0x2
  addiu a1,a1,0x140
  sll a2,s3,0x4
  jal CharRender
  andi a2,a2,0xff
  ;Go to the next character
  addiu s0,s0,0x1
  j ANIME_READ_CHAR
  addu s2,s2,v0

  ANIME_REDIRECT_CODE:
  ;Sign extend here to handle negative values
  lb a0,0x2(s0)
  lbu a1,0x1(s0)
  sll a0,a0,0x8
  or a0,a0,a1
  j ANIME_READ_CHAR
  addu s0,s0,a0

  ;Correctly calculate the string length with redirects and VWF
  ;a0 = str pointer
  ;v0 = result
  STRLEN_VWF:
  clear v0
  STRLEN_LOOP:
  lbu t0,0x0(a0) :: nop
  ;Return on 0
  beq t0,zero,STRLEN_RET
  ;Skip 0x1e
  li t1,0x1e
  beq t0,t1,STRLEN_SKIP
  ;Handle redirect on 0x1f
  li t1,0x1f
  beq t0,t1,STRLEN_REDIRECT
  ;Simplified VWF
  li t1,0x20
  beq t0,t1,STRLEN_SHORT
  li t1,0x69
  beq t0,t1,STRLEN_SHORT
  li t1,0x6c
  beq t0,t1,STRLEN_SHORT :: nop
  addiu v0,v0,0x1
  ;Increase v0 and loop
  STRLEN_SHORT:
  addiu v0,v0,0x1
  STRLEN_SKIP:
  j STRLEN_LOOP
  addiu a0,a0,0x1
  STRLEN_REDIRECT:
  lb t0,0x2(a0)
  lbu t1,0x1(a0)
  sll t0,t0,0x8
  or t0,t0,t1
  j STRLEN_LOOP
  addu a0,a0,t0
  STRLEN_RET:
  jr ra
  srl v0,v0,0x1
.endarea

;Anime sections text
;s0 = string pointer
;s1 = char num
;s2 = x position
;s3 = y position
;In normal execution, a sjis character is read and drawn with the following exceptions:
;0x6565: break and return
;0x7a7a: reset x position (s2 = 8)
;0x0000: newline: Skip 3 bytes (s0+=3), s1=0, s2=0, s3+=1
.org 0x8004920c
.area 0x88
  sw ra,0x20(sp)
  li s2,0x0
  ANIME_READ_CHAR:
  ;Check single-byte charcodes
  lbu a0,0x0(s0)
  li a2,0x1e
  beq a0,a2,ANIME_SPACING
  li a2,0x1f
  beq a0,a2,ANIME_REDIRECT
  li a2,0x0a
  beq a0,a2,ANIME_NEWLINE
  ;Check double-byte charcodes
  lbu a2,0x1(s0)
  sll a1,a0,0x8
  or a1,a1,a2
  beq a1,zero,ANIME_NEWLINE_DOUBLE
  li a2,0x7a7a
  beq a1,a2,ANIME_RESETX
  li a2,0x6565
  beq a1,a2,ANIME_RETURN :: nop
  ;Setup CharRender parameters
  j ANIME_RENDER_CODE :: nop
  ;Start a new line
  ANIME_NEWLINE_DOUBLE:
  addiu s0,s0,0x2
  ANIME_NEWLINE:
  addiu s0,s0,0x1
  addiu s3,s3,0x1
  j ANIME_READ_CHAR
  li s2,0x0
  ;Add the next byte to s2
  ANIME_SPACING:
  lbu a0,0x1(s0)
  addiu s0,s0,0x2
  j ANIME_READ_CHAR
  addu s2,s2,a0
  ;Reset s2 and continue
  ANIME_RESETX:
  addiu s0,s0,0x2
  j ANIME_READ_CHAR
  li s2,0x0
  ;Add the redirect value to s0 and continue
  ANIME_REDIRECT:
  j ANIME_REDIRECT_CODE :: nop
.endarea
.org 0x80049294
  ANIME_RETURN:

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

;Hook the strlen call for character names
.org 0x8008ee18
  jal STRLEN_VWF
;Tweak the spacing (Add 5 instead of 4)
.org 0x8008ee38
  addiu v0,v0,0x5
;Hook for battle dialog choices
.org 0x80070834
  jal STRLEN_VWF
;Hook for spell names
.org 0x8003bbd8
  jal STRLEN_VWF
;Hook for dialog choices and add some space
.org 0x8007e4a4
  jal STRLEN_VWF
  nop
  addiu s3,v0,0x1
;Hook for book monster name
.org 0x800879ac
  jal STRLEN_VWF


;Swap Circle and Cross
.org 0x80057010
  j CONTROLLER :: nop
  CONTROLLER_RETURN:

;Enable debug mode
.ifdef DEBUG
.org 0x80056354
  li s0,0x1
  .skip 4 ;jal
  sh s0,0x4054(at)
.endif

;nop printf to avoid errors with replaced error strings
.org 0x8009b910
  nop
  jr ra
  nop

.close

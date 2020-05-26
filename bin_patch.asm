.psx

;Libary functions
ClearImage       equ 0x8009d0fc
LoadImage        equ 0x8009d190
MoveImage        equ 0x8009d258
DrawSync         equ 0x8009cf68
strlen           equ 0x8009b920
;Other locations/values
InitStringStruct equ 0x80077da8
RenderString     equ 0x8007c4e8
ClearString      equ 0x800782e0
DebugEnabled     equ 0x800f4054
FontTable        equ 0x800c49cc
FontVRamX        equ 1024 - (256 / 4)
FontVRamY        equ 48

.open "data/repack/SCPS_100.23",0x8000F800

;Manual ptr replacement generated by the tool
.include "data/manualptrs.asm"

;Replace error codes
.org 0x80017470
.area 0x21E
  .include "data/zones.asm"
.endarea

;Replace the anime text rendering function
.org 0x80048f24
.area 0x2C0
  ;----------------------------------
  ;Lookup tables
  ;----------------------------------
  ;ASCII to SJIS lookup table
  SJIS_LOOKUP:
  .sjisn "　！”＃＄％＆"
  ;Fix ' since it doesn't get encoded correctly
  .db 0x81 :: .db 0x66
  ;Also change + to * and _ to ;
  .sjisn "（）＋＋，－．／０１２３４５６７８９：＿〈＝〉？＠"
  .sjisn "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿　"
  .sjisn "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｝｜～"

  ;VWF lookup table
  VWF_LOOKUP:
  .import "data/vwf.bin"
  .definelabel VWF_LOOKUP2,VWF_LOOKUP + 0x60

  ESCAPE_STRING:
  .ascii "%s" :: .db 0xa :: .db 0x0
  NAMEPLATE_STRING:
  .asciiz " %s" :: .db 0x0

  .align


  ;----------------------------------
  ;MoveImage char rendering function
  ;----------------------------------
  ;a0 = ASCII character
  ;a1 = x position
  ;a2 = y position
  CharRender:
  ;Setup stack
  addiu sp,sp,-0x20
  sw ra,0x0(sp)
  ;Check if it's a space
  li v0,0x20
  bne a0,v0,@@nospace
  ;Return the space VWF value
  @@space:
  li v0,VWF_LOOKUP2
  li a0,0x20
  addu v0,v0,a0
  j @@ret
  lbu t9,0x0(v0)
  @@nospace:
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
  @@font:
  addiu t0,t0,0x5
  addiu v1,v1,-0x1
  ;If 0x100 is reached, just render a space
  beq v1,zero,@@space
  lbu t1,0x0(t0) :: nop
  bne v0,t1,@@font
  lbu t1,0x1(t0) :: nop
  bne a0,t1,@@font :: nop
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
  @@ret:
  lw ra,0x0(sp)
  addiu sp,sp,0x20
  jr ra
  move v0,t9

  ;----------------------------------
  ;Anime related code (moved here to fit)
  ;----------------------------------
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
.endarea


;Set half width characters as default in the StringToStruct function
.org 0x8007ad3c
  li s4,0x1
.org 0x8007ad4c
  sh s4,0x8(s2)


;Replace error codes
.org 0x80016b54
.area 0x34C
  ;----------------------------------
  ;CopyASCII function
  ;----------------------------------
  ;Copy a character from a string to a buffer, converting it to SJIS if ASCII
  ;Also handles various control codes found in string
  ;t5 = temp
  ;a0 = char
  ;a1 = source pointer
  ;s0 = dest pointer
  CopyASCII:
  ;Copy both bytes for sjis characters
  li t5,0x7f
  bgt a0,t5,@@sjis
  ;0x1f: the string was redirected to another location
  li t5,0x1f
  beq a0,t5,@@redirect
  ;0x1e: insert $c
  li t5,0x1e
  beq a0,t5,@@insertC
  ;If < 0x20, just copy the byte
  li t5,0x20
  blt a0,t5,@@copy
  ;Handle space
  li t5,0x20
  beq a0,t5,@@space
  ;Handle @
  li t5,0x40
  beq a0,t5,@@copy
  ;Handle char codes that start with $
  li t5,0x24
  beq a0,t5,@@ccodes
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
  @@space:
  li t5,0x81
  li a0,0x40
  sb t5,0x0(s0)
  sb a0,0x1(s0)
  addiu s0,s0,0x2
  addiu a1,a1,0x1
  jr ra :: nop
  ;Copy 2 bytes for SJIS
  @@sjis:
  lbu t5,0x1(a1)
  sb a0,0x0(s0)
  sb t5,0x1(s0)
  addiu a1,a1,0x2
  addiu s0,s0,0x2
  jr ra :: nop
  ;Copy 2 bytes for control codes
  @@ccodes:
  lbu t5,0x1(a1)
  sb a0,0x0(s0)
  sb t5,0x1(s0)
  addiu a1,a1,0x2
  addiu s0,s0,0x2
  ;Check for $g code
  li a0,0x67
  bne a0,t5,@@ccodesDone
  ;For $g codes, keep copying until it finds numbers
  @@ccodesG:
  lbu t5,0x0(a1)
  li a0,0x2f
  ble t5,a0,@@ccodesDone
  li a0,0x3a
  bge t5,a0,@@ccodesDone
  lbu t5,0x0(a1)
  addiu a1,a1,0x1
  sb t5,0x0(s0)
  addiu s0,s0,0x1
  j @@ccodesG :: nop
  @@ccodesDone:
  jr ra
  ;Insert $c
  @@insertC:
  li t5,0x24
  sb t5,0x0(s0)
  li t5,0x63
  sb t5,0x1(s0)
  addiu a1,a1,0x1
  addiu s0,s0,0x2
  jr ra :: nop
  ;Just copy the character
  @@copy:
  sb a0,0x0(s0)
  addiu a1,a1,0x1
  addiu s0,s0,0x1
  jr ra
  ;Add the new address to the source and return
  @@redirect:
  lbu t5,0x2(a1)
  lbu a0,0x1(a1)
  sll t5,t5,0x8
  or t5,t5,a0
  addu a1,a1,t5
  jr ra :: nop

  ASCII:
  ;Return to normal execution to handle %
  beq v1,v0,@@perc
  ;Call the function
  move a0,v1
  jal CopyASCII
  move a1,s1
  j ASCII_RETURN
  move s1,a1
  @@perc:
  j ASCII_RETURN_PERC :: nop

  ASCII_SPRINTF:
  ;Call the function
  move a0,v0
  jal CopyASCII
  move a1,v1
  j ASCII_SPRINTF_RETURN
  move v1,a1

  ASCII_SPRINTF_NUM:
  ;Insert two spaces instead of one
  sb v0,0x1(v1)
  li v0,0x40 :: nop
  sb v0,0x0(v1)
  sb v0,0x2(v1)
  addiu v1,v1,0x2
  j ASCII_SPRINTF_NUM_RETURN
  addiu a3,a3,0x2


  ;----------------------------------
  ;VWF function
  ;----------------------------------
  ;s1 = character
  ;r20 = spacing
  VWF:
  ;Skip japanese characters
  li t1,0xd0
  li t2,VWF_LOOKUP
  bge s1,t1,@@jap
  ;Get the VWF width from the lookup table
  addu t2,t2,s1
  lbu t1,0x0(t2)
  ;Check if > 0x10
  li t2,0x10
  bgt t1,t2,@@align :: nop
  j VWF_RETURN
  addu s4,s4,t1
  ;Set the X position (*2) instead of adding to it
  @@align:
  sll t1,t1,0x1
  j VWF_RETURN
  move s4,t1
  ;Default to 0x8 for japanese characters
  @@jap:
  addiu s4,s4,0x8
  j VWF_RETURN :: nop

  ;Check if there are 2 consecutive 0s and move to the next line
  VWF_FIX:
  lbu s1,0x38(v0)
  lbu v0,0x39(v0) :: nop
  addu v0,s1,v0
  bgt v0,zero,@@notZero :: nop
  j VWF_FIX_ENDLINE
  li v0,0x20
  @@notZero:
  j VWF_FIX_RETURN
  li v0,0x20


  ;----------------------------------
  ;Controller stuff
  ;----------------------------------
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


  ;----------------------------------
  ;Singular experience point
  ;----------------------------------
  ;a1 = str pointer
  ;sp+0x20 = exp
  EXP_POINT:
  lw t0,0x20(sp)
  li t1,0x1
  beq t0,t1,@@one
  addiu t0,a1,0x10
  li t1,0x73
  sb t1,0x0(t0)
  li t1,0x2e
  sb t1,0x1(t0)
  j @@jal
  @@one:
  li t1,0x2e
  sb t1,0x0(t0)
  li t1,0x20
  sb t1,0x1(t0)
  @@jal:
  jal RenderString :: nop
  j EXP_POINT_RETURN :: nop


  ;----------------------------------
  ;strlen function
  ;----------------------------------
  ;Correctly calculate the string length with redirects and VWF
  ;a0 = str pointer
  ;v0 = result
  STRLEN_VWF:
  clear v0
  @@loop:
  lbu t0,0x0(a0) :: nop
  ;Return on 0
  beq t0,zero,@@ret
  ;Skip 0x1e
  li t1,0x1e
  beq t0,t1,@@skip
  ;Handle redirect on 0x1f
  li t1,0x1f
  beq t0,t1,@@redirect
  ;Simplified VWF
  li t1,0x20
  beq t0,t1,@@short
  li t1,0x69
  beq t0,t1,@@short
  li t1,0x6c
  beq t0,t1,@@short :: nop
  addiu v0,v0,0x1
  ;Increase v0 and loop
  @@short:
  addiu v0,v0,0x1
  @@skip:
  j @@loop
  addiu a0,a0,0x1
  @@redirect:
  lb t0,0x2(a0)
  lbu t1,0x1(a0)
  sll t0,t0,0x8
  or t0,t0,t1
  j @@loop
  addu a0,a0,t0
  @@ret:
  jr ra
  srl v0,v0,0x1

  BOOK_VWF:
  bne a0,zero,@@notzero :: nop
  li a0,0x20
  @@notzero:
  ;Get VWF value
  li t0,VWF_LOOKUP
  addu t0,t0,a0
  lbu t1,0x0(t0)
  ;Add it to the x position
  li t0,0x800db29c
  lw t2,0x0(t0) :: nop
  addu t1,t2,t1
  j BOOK_VWF_RETURN
  sw t1,0x0(t0)
.endarea

.org 0x80017F7C
.area 0x3AE
  .include "data/softsubs.asm"

  CURRENT_SUB:
  .dw 0  ;Pointer
  .dw 0  ;Current frame
  .dw 0  ;Struct pointer

  ;----------------------------------
  ;Softsubs function
  ;----------------------------------
  ;a0 = str pointer
  LineRender:
  ;Setup stack
  addiu sp,sp,-0x30
  sw ra,0x0(sp)
  sw a0,0x4(sp)
  sw a1,0x8(sp)
  sw a2,0xc(sp)
  sw a3,0x2c(sp)
  ;Check current struct pointer
  li a0,CURRENT_SUB + 0x8
  lw a0,0x0(a0) :: nop
  beq a0,zero,@@initStruct :: nop
  jal ClearString :: nop
  @@initStruct:
  ;Call InitStringStruct
  li a0,0x3
  li a1,0x3
  li a2,0x18
  li a3,0x24
  li v0,0x1b
  sw v0,0x10(sp)
  sw zero,0x14(sp)
  sw zero,0x18(sp)
  sw zero,0x1c(sp)
  sw zero,0x20(sp)
  sw zero,0x24(sp)
  jal InitStringStruct
  sw zero,0x28(sp)
  ;Store this in memory
  li a0,CURRENT_SUB + 0x8
  sw v0,0x0(a0)
  move a0,v0
  ;Call RenderString
  lw a1,0x4(sp)
  jal RenderString :: nop
  ;Return
  lw ra,0x0(sp)
  lw a0,0x4(sp)
  lw a1,0x8(sp)
  lw a2,0xc(sp)
  lw a3,0x2c(sp)
  addiu sp,sp,0x30
  jr ra :: nop

  ;----------------------------------
  ;Called every frame, check the timing
  ;----------------------------------
  SUB_FRAME:
  addiu sp,sp,-0x10
  sw ra,0x0(sp)
  ;Check the current sub pointer
  li t0,CURRENT_SUB
  lw a0,0x0(t0) :: nop
  ;Jump out if 0
  beq a0,zero,@@ret
  ;Increase the frame counter
  lw t2,0x4(t0) :: nop
  addiu t2,t2,0x1
  sw t2,0x4(t0)
  ;Get the next frame number and compare it
  lbu t0,0x1(a0)
  lbu t3,0x0(a0)
  sll t0,t0,0x8
  or t0,t0,t3
  bne t0,t2,@@ret
  ;Check the byte after for 0
  addiu a0,a0,0x2
  lbu t0,0x0(a0) :: nop
  beq t0,zero,@@clear :: nop
  ;Render the current line
  jal LineRender :: nop
  ;Read until 0
  @@loop:
  lbu t0,0x1(a0) :: nop
  bne t0,zero,@@loop
  addiu a0,a0,0x1
  j @@done
  @@clear:
  ;Clear the current line
  li t0,CURRENT_SUB + 0x8
  move t1,a0
  lw a0,0x0(t0)
  sw zero,0x0(t0)
  jal ClearString :: nop
  move a0,t1
  @@done:
  ;Store the pointer back in memory
  addiu a0,a0,0x1
  li t0,CURRENT_SUB
  sw a0,0x0(t0)
  @@ret:
  lw ra,0x0(sp)
  addiu sp,sp,0x10
  jr ra :: nop

  ;----------------------------------
  ;Called when a sound file is played
  ;----------------------------------
  ;t0 = sound file?
  SUB_START:
  addiu sp,sp,-0x10
  sw ra,0x0(sp)
  sw t1,0x4(sp)
  sw t2,0x8(sp)
  sw v0,0xc(sp)
  ;Check if the sound file matches one of the softsubs
  li t1,SUB_DATA :: nop
  @@loop:
  lw t2,0x0(t1) :: nop
  beq t2,zero,@@call :: nop
  beq t2,t0,@@found :: nop
  j @@loop
  addiu t1,t1,0x8
  ;Found one, set the values
  @@found:
  lw t2,0x4(t1)
  li t1,CURRENT_SUB
  sw zero,0x4(t1)
  sw t2,0x0(t1)
  ;Regular call
  @@call:
  lw t1,0x4(sp)
  jal 0x800ae218
  lw t2,0x8(sp)
  lw v0,0xc(sp)
  lw ra,0x0(sp)
  addiu sp,sp,0x10
  jr ra :: nop
.endarea

;----------------------------------
;Anime sections text
;----------------------------------
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
  beq a0,a2,@@spacing
  li a2,0x1f
  beq a0,a2,@@redirect
  li a2,0x0a
  beq a0,a2,@@newline
  ;Check double-byte charcodes
  lbu a2,0x1(s0)
  sll a1,a0,0x8
  or a1,a1,a2
  beq a1,zero,@@newlineDouble
  li a2,0x7a7a
  beq a1,a2,@@resetx
  li a2,0x6565
  beq a1,a2,ANIME_RETURN :: nop
  ;Setup CharRender parameters
  j ANIME_RENDER_CODE :: nop
  ;Start a new line
  @@newlineDouble:
  addiu s0,s0,0x2
  @@newline:
  addiu s0,s0,0x1
  addiu s3,s3,0x1
  j ANIME_READ_CHAR
  li s2,0x0
  ;Add the next byte to s2
  @@spacing:
  lbu a0,0x1(s0)
  addiu s0,s0,0x2
  j ANIME_READ_CHAR
  addu s2,s2,a0
  ;Reset s2 and continue
  @@resetx:
  addiu s0,s0,0x2
  j ANIME_READ_CHAR
  li s2,0x0
  ;Add the redirect value to s0 and continue
  @@redirect:
  j ANIME_REDIRECT_CODE :: nop
.endarea
.org 0x80049294
  ANIME_RETURN:


;----------------------------------
;Load text parsing
;----------------------------------
;Chapter number
;v1 = save name ptr
;a0 = dest string
;a3 = save name position
.org 0x80093084
.area 0x44,0x0
  ;Write "Ch."
  li v0,0x43
  sb v0,0x0(a0)
  li v0,0x68
  sb v0,0x1(a0)
  li v0,0x2e
  sb v0,0x2(a0)
  ;Read the chapter number 第１章 (2nd byte of sjis number)
  ;Subtract 0x1f to convert to ASCII number
  lbu v0,0x3(v1) :: nop
  addiu v0,v0,-0x1f
  sb v0,0x3(a0)
  ;Terminate with 0
  sb zero,0x4(a0)
.endarea

;Place name
;v1 = save name ptr
;a0 = dest string
.org 0x800930f0
.area 0x3C,0x0
  clear t0
  li t1,0x10
  li t3,0x80
  @@loop:
  ;Sum all the characters in t0 until the character is < 0x80
  lbu v0,0x0(v1)
  lbu t2,0x1(v1)
  blt v0,t3,@@break
  addiu t1,t1,-0x2
  addu t0,t0,v0
  addu t0,t0,t2
  bne t1,zero,@@loop
  addiu v1,v1,0x2
  @@break:
  j CHAPTER_LOOKUP
  CHAPTER_RETURN:
.endarea

;Replace error codes
.org 0x80017D5C
.area 0x8E
  CHAPTER_LOOKUP:
  ;Search for the correct lookup
  li t2,ZONE_LOOKUP
  @@lookup:
  lh t1,0x0(t2)
  addiu t2,t2,0x2
  beq t1,zero,@@nazo :: nop
  bne t1,t0,@@lookup
  addiu t2,t2,0x2
  ;Found, get the pointer to the string and copy it
  lh t0,-0x2(t2)
  li t1,ZONE_START
  addu t0,t0,t1
  clear a3
  @@copy:
  lbu t1,0x0(t0)
  addiu t0,t0,0x1
  sb t1,0x0(a0)
  addiu a3,a3,0x1
  bne zero,t1,@@copy
  addiu a0,a0,0x1
  j CHAPTER_RETURN
  @@nazo:
  ;Write "??? "
  li t0,0x203f3f3f
  sw t0,0x0(a0)
  addiu a0,a0,0x4
  addiu a3,a3,0x7
  ;Read and write the numbers
  ;Go back 5 bytes since the ptr is at the end of the string
  @@numberLoop:
  lbu v0,-0x5(v1)
  li t1,0x40
  beq v0,t1,@@done
  addiu v0,v0,-0x1f
  sb v0,0x0(a0)
  addiu v1,v1,0x2
  j @@numberLoop
  addiu a0,a0,0x1
  @@done:
  j CHAPTER_RETURN
  sb zero,0x0(a0)
.endarea


;----------------------------------
;ASCII hooks
;----------------------------------
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
;Write 2 spaces for each missing number in %nd sprintf codes
.org 0x800774a4
  j ASCII_SPRINTF_NUM
  .skip 4
  ASCII_SPRINTF_NUM_RETURN:


;----------------------------------
;VWF hooks
;----------------------------------
;Replace the fixed with for half characters
.org 0x8007bae4
  j VWF
  .skip 4
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
.org 0x80078154
  li v0,0x14

;.org 0x8007a548
;  nop


;----------------------------------
;Monster book VWF
;----------------------------------
;Store character index in stack in place of a nop
.org 0x8007c458
  sw a3,0xc(sp)
;Store 0 by default since the space gets skipped
.org 0x8007c400
  sw zero,0xc(sp)
;Replace the 0x8007c1f4 function call
.org 0x8007c4d0
  j BOOK_VWF
  lw a0,0xc(sp)
  BOOK_VWF_RETURN:


;----------------------------------
;strlen hooks
;----------------------------------
;Character names
.org 0x8008ee18
  jal STRLEN_VWF
;Tweak the spacing (Add 5 instead of 4)
.org 0x8008ee38
  addiu v0,v0,0x5
;Battle dialog choices
.org 0x80070834
  jal STRLEN_VWF
;Spell names
.org 0x8003bbd8
  jal STRLEN_VWF
;Dialog choices and add some space
.org 0x8007e4a4
  jal STRLEN_VWF
  nop
  addiu s3,v0,0x1
;Battle related (critical, spell names, etc)
.org 0x80040ab8
  jal STRLEN_VWF
  .skip 4
  sll t1,v0,0x1
;Monster book name
.org 0x800879ac
  jal STRLEN_VWF


;----------------------------------
;Softsubs hooks
;----------------------------------
;Sound open
.org 0x8007d938
  jal SUB_START
;Frame
.org 0x800a79d0
  j SUB_FRAME


;----------------------------------
;Misc
;----------------------------------
;Singular experience point
.org 0x80045144
  j EXP_POINT
  nop
  EXP_POINT_RETURN:

;Reduce spacing for menu abilities
.org 0x800801d4
.area 0x8,0x0
  li a1,ESCAPE_STRING
.endarea

;Change nameplate string
.org 0x80040c38
.area 0x8,0x0
  li a1,NAMEPLATE_STRING
.endarea

;Change battle items string
.org 0x80010B64
  .ascii "%s %s" :: .db 0x83 :: .db 0x55 :: .ascii "x%2d" :: .db 0x1e :: .db 0xa :: .db 0x1e :: .db 0x0

;Extend 1st movie to full length
.org 0x800b6d30
  .dw 0x3fa

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


;----------------------------------
;Textbox tweaks
;----------------------------------
;Formation text
.org 0x800c57c4 ;x
  ;dh 0x1a ;0x19
.org 0x8008a0d0 ;width (First time)
  addiu a3,a1,0xb ;0x9
.org 0x8008a308 ;width (Update)
  addiu v0,a2,0xb ;0x9

;Menu magic list
.org 0x80082f28 ;width
  li v0,0x19 ;0x18

;Status magic
.org 0x800803a0 ;LV (First time)
  addiu a1,s1,0x6b ;0x60
.org 0x800804e4 ;LV (Update)
  addiu a1,s1,0x6b ;0x60
.org 0x800803c0 ;EXP (First time)
  addiu a1,s1,0x8f ;0x88
.org 0x80080504 ;EXP (Update)
  addiu a1,s1,0x8f ;0x88

;Pietro and his friends run away
.org 0x8003d7a8 ;x/width
  li a1,0x6  ;0x8
  li a3,0x22 ;0x20

;You have defeated the monsters!
.org 0x8003d4f8 ;x/width
  li a1,0x8  ;0xa
  .skip 4
  li a3,0x20 ;0x1e

;Are you sure? (escape)
.org 0x8003d320 ;x/width
  li a1,0xd  ;0xc
  .skip 4
  li a3,0x18 ;0x1c

;The enemy caught up
.org 0x8003d8e8 ;x/width
  li a1,0xa  ;0x9
  .skip 4
  li a3,0x1d ;0x1f

;Battle magic list
.org 0x8003bc58 ;width
  addiu a3,a3,0xf ;0x6

;Battle abilities list
.org 0x8003bca8 ;width
  addiu a3,a3,0xd ;0x2

;Center monster book name
.org 0x800879b4
  move v1,v0
  .skip 4
  li a0,0x7

.close

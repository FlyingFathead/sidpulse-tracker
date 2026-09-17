; Compact standalone SIDpulse PRG wrapper. BASIC RUN enters SYS 2061.
; Assemble without a load address; the Python exporter supplies it:
; 64tass --nostart -o sidpulse/assets/prg-loader-squeezed.bin sidpulse/export/prg_loader_squeezed.asm
;
; Poll CIA1 timer A with IRQs masked. The compiled player sets the timer latch
; for each tempo, including multi-call slow ticks, exactly as in PSID playback.
; This program owns the machine while playing; RUN/STOP returns to BASIC.
; Start from the normal C64 BASIC environment (KERNAL and I/O mapped in).
* = $0801
        .word basic_end
        .word 10
        .byte $9e
        .text "2061"
        .byte 0
basic_end:
        .word 0
entry:
        php
        sei
        cld
        ldx #3
save_zp:
        lda $f8,x
        sta saved_zp,x
        dex
        bpl save_zp
        lda #<banner
        ldx #>banner
        jsr print
        lda #<song_title
        ldx #>song_title
        jsr print
        lda #13
        jsr $ffd2
        lda #<song_author
        ldx #>song_author
        jsr print
        lda #13
        jsr $ffd2
        lda #<target_text
        ldx #>target_text
        jsr print
        lda $02a6
        cmp target_pal
        beq start_music
        lda #<mismatch
        ldx #>mismatch
        jsr print
        jmp return_basic
start_music:
        lda #<instructions
        ldx #>instructions
        jsr print
        lda #$7f
        sta $dc0d               ; no CIA1 IRQ while we poll its timer flag
        lda #0
        sta $dc0e               ; CPU clock, continuous mode, timer stopped
        sta $dc03               ; keyboard rows are inputs
        lda #$ff
        sta $dc02               ; keyboard columns are outputs
        lda $dc0d               ; discard pending flags before the first tick
        lda #0
        ldx #24
reset_sid:
        sta $d400,x
        dex
        bpl reset_sid
        ldy #40                 ; > 50 ms at PAL/NTSC: settle old SID envelopes
settle_outer:
        ldx #0
settle_inner:
        dex
        bne settle_inner
        dey
        bne settle_outer
        jsr $09b4               ; SID init includes the first music tick
wait_tick:
        lda #$7f
        sta $dc00               ; select the column containing RUN/STOP
        lda $dc01
        and #$80
        beq stop_music
        lda $dc0d               ; read acknowledges timer-A underflow
        and #1
        beq wait_tick
        jsr $09b7
        jmp wait_tick
stop_music:
        lda #0
        sta $dc0e
        ldx #24
silence:
        sta $d400,x
        dex
        bpl silence
        jsr $ff84               ; restore normal C64 I/O
        jsr $ff81               ; restore screen and PAL/NTSC keyboard timer
return_basic:
        ldx #3
restore_zp:
        lda saved_zp,x
        sta $f8,x
        dex
        bpl restore_zp
        plp
        rts
print:
        sta $f8
        stx $f9
        ldy #0
print_next:
        lda ($f8),y
        beq print_done
        jsr $ffd2
        iny
        bne print_next
print_done:
        rts
saved_zp: .fill 4,0
banner: .byte 147,142
        .text "SIDPULSE TRACKER",13,13,0
instructions:
        .text 13,13,"PLAYING - RUN/STOP RETURNS TO BASIC",13,0
mismatch:
        .text 13,13,"THIS TUNE USES A DIFFERENT VIDEO CLOCK.",13
        .text "EXPORT FOR THIS C64'S PAL/NTSC SETTING.",13,0
song_title: .fill 33,0
song_author: .fill 33,0
target_text: .fill 16,0
target_pal: .byte 1

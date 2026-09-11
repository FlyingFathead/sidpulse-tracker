; SIDpulse register-program player, original implementation.
; Assemble: 64tass --nostart -o sidpulse/assets/player.bin sidpulse/export/player.asm
; Load $1000, init $1000, play $1003. One SID, PAL CIA1 timer.
; Uses zero page $f8..$fb, owns $1000..$11ff and compiled data at $1200+.
; Record: CIA period LE16, idle calls, pair count, [SID register,value] pairs.
; Register $19 is a gate settling delay token; it is never written to SID.
; Sequence: LE16 record addresses, zero terminator. Dedup never reorders writes.
* = $1000
        jmp init
        jmp play
stream = $f8
record = $fa
init:
        cld
        lda sequence
        sta stream
        lda sequence+1
        sta stream+1
        lda #0
        sta done
        sta ticks_left
        sta lastlo
        sta lasthi
        ldx #24
clear:
        sta $d400,x
        dex
        bpl clear
        jmp play
play:
        cld
        lda done
        beq checkhold
        rts
checkhold:
        lda ticks_left
        beq active
        dec ticks_left
        rts
active:
        ldy #0
        lda (stream),y
        sta record
        iny
        lda (stream),y
        sta record+1
        ora record
        bne found
        lda loop_sequence
        ora loop_sequence+1
        beq finish
        lda loop_sequence
        sta stream
        lda loop_sequence+1
        sta stream+1
        jmp active
finish:
        lda #0
        sta $d404
        sta $d40b
        sta $d412
        inc done
        rts
found:
        clc
        lda stream
        adc #2
        sta stream
        bcc samepage
        inc stream+1
samepage:
        ldy #0
        lda (record),y
        cmp lastlo
        bne setperiod
        iny
        lda (record),y
        cmp lasthi
        beq periodready
setperiod:
        ldy #0
        lda (record),y
        sta lastlo
        sta $dc04
        iny
        lda (record),y
        sta lasthi
        sta $dc05
        ; Force the changed latch now, avoiding a tick at the old tempo.
        lda $dc0e
        ora #$11
        sta $dc0e
periodready:
        ldy #2
        lda (record),y
        sta ticks_left
        iny
        lda (record),y
        sta remaining
        iny
        lda remaining
        beq finished
nextwrite:
        lda (record),y
        tax
        iny
        lda (record),y
        iny
        cpx #$19
        beq gap
        sta $d400,x
        jmp consumed
gap:
        ldx #6
waitgate:
        dex
        bne waitgate
consumed:
        dec remaining
        bne nextwrite
finished:
        rts
.fill $11eb-*,0
ticks_left: .byte 0
lastlo: .byte 0
lasthi: .byte 0
remaining: .byte 0
done: .byte 0
sequence: .word 0
loop_sequence: .word 0
.fill $1200-*,0

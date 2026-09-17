; SIDpulse lossless, resident stream player. No whole-song decompression buffer.
; Build raw-pair variant with -D TEMPLATES=0, template variant with -D TEMPLATES=1.
; 64tass --nostart -D TEMPLATES=0 -o sidpulse/assets/squeeze-player.bin sidpulse/export/player_channels.asm
; Entry points PLAYER_LOAD / PLAYER_LOAD+3; zero page $f8..$fb.
; PLAYER_LOAD is $1000 for PSID or $09b4 for the compact PRG wrapper.
; Five independently factored streams: voices 0..2, global writes, tick schedule.
; Stream descriptor: length (1..255), repetitions (1..255), LE16 word-pool address.
; A zero length ends a stream. The word pool contains absolute record pointers.
; Schedule record: CIA period LE16, idle calls, run count, ordered lane IDs.
; Raw write record: pair count, [SID register offset,value] pairs. $19 = gate delay.
; Template write record: template ID, values. Template: count, register offsets.
; The host patches template-low/high table operands in the template variant.
; Streams only share immutable words/records. All mutable state is in this image.
* = PLAYER_LOAD
        jmp init
        jmp play
scratch = $f8
record = $fa
init:
        cld
        lda #0
        sta done
        sta ticks_left
        sta lastlo
        sta lasthi
        ldx #24
clear_sid:
        sta $d400,x
        dex
        bpl clear_sid
        jsr reset_streams
        jmp play
reset_streams:
        ldx #4
reset_one:
        lda starts_lo,x
        sta commands_lo,x
        lda starts_hi,x
        sta commands_hi,x
        lda #0
        sta remaining,x
        sta repeats,x
        dex
        bpl reset_one
        rts
play:
        cld
        lda done
        beq check_hold
        rts
check_hold:
        lda ticks_left
        beq active
        dec ticks_left
        rts
active:
        ldx #4
        jsr fetch
        bcc schedule_found
        lda loop_enabled
        beq finish
        jsr reset_streams
        jmp active
finish:
        lda #0
        sta $d404
        sta $d40b
        sta $d412
        inc done
        rts
schedule_found:
        ldy #0
        lda (record),y
        cmp lastlo
        bne set_period
        iny
        lda (record),y
        cmp lasthi
        beq period_ready
set_period:
        ldy #0
        lda (record),y
        sta lastlo
        sta $dc04
        iny
        lda (record),y
        sta lasthi
        sta $dc05
        lda $dc0e
        ora #$11
        sta $dc0e
period_ready:
        ldy #2
        lda (record),y
        sta ticks_left
        iny
        lda (record),y
        sta runs_left
        lda record
        sta schedule_lo
        lda record+1
        sta schedule_hi
        lda #4
        sta schedule_index
next_run:
        lda runs_left
        beq finished
        lda schedule_lo
        sta scratch
        lda schedule_hi
        sta scratch+1
        ldy schedule_index
        lda (scratch),y
        tax
        inc schedule_index
        jsr fetch
        ; EOF cannot occur here in a compiler-verified stream.
        bcc write_record
        jmp finish
write_record:
        ldy #0
.if TEMPLATES
        lda (record),y
        tax
template_low_load:
        lda $ffff,x
        sta scratch
template_high_load:
        lda $ffff,x
        sta scratch+1
        lda (scratch),y
.else
        lda (record),y
.endif
        sta pairs_left
        iny
next_write:
.if TEMPLATES
        lda (scratch),y
        tax
        lda (record),y
        iny
.else
        lda (record),y
        tax
        iny
        lda (record),y
        iny
.endif
        cpx #$19
        beq gap
        sta $d400,x
        jmp consumed
gap:
        ldx #6
wait_gate:
        dex
        bne wait_gate
consumed:
        dec pairs_left
        bne next_write
        dec runs_left
        jmp next_run
finished:
        rts
; X selects a stream. Returns its next record address in $fa/$fb, C clear.
; C set means end of stream. No recursive calls or output/history buffer.
fetch:
        lda remaining,x
        bne read_word
        lda repeats,x
        beq new_block
        dec repeats,x
        lda lengths,x
        sta remaining,x
        lda origins_lo,x
        sta cursors_lo,x
        lda origins_hi,x
        sta cursors_hi,x
        jmp read_word
new_block:
        lda commands_lo,x
        sta scratch
        lda commands_hi,x
        sta scratch+1
        ldy #0
        lda (scratch),y
        bne block_found
        sec
        rts
block_found:
        sta lengths,x
        sta remaining,x
        iny
        lda (scratch),y
        sec
        sbc #1
        sta repeats,x
        iny
        lda (scratch),y
        sta origins_lo,x
        sta cursors_lo,x
        iny
        lda (scratch),y
        sta origins_hi,x
        sta cursors_hi,x
        clc
        lda scratch
        adc #4
        sta commands_lo,x
        lda scratch+1
        adc #0
        sta commands_hi,x
read_word:
        lda cursors_lo,x
        sta scratch
        lda cursors_hi,x
        sta scratch+1
        ldy #0
        lda (scratch),y
        sta record
        iny
        lda (scratch),y
        sta record+1
        clc
        lda scratch
        adc #2
        sta cursors_lo,x
        lda scratch+1
        adc #0
        sta cursors_hi,x
        dec remaining,x
        clc
        rts
; Configuration patched by the host, not mutable during replay.
starts_lo: .fill 5,0
starts_hi: .fill 5,0
loop_enabled: .byte 0
; Fixed workspace (no data-dependent allocation).
workspace:
commands_lo: .fill 5,0
commands_hi: .fill 5,0
cursors_lo: .fill 5,0
cursors_hi: .fill 5,0
origins_lo: .fill 5,0
origins_hi: .fill 5,0
lengths: .fill 5,0
remaining: .fill 5,0
repeats: .fill 5,0
ticks_left: .byte 0
lastlo: .byte 0
lasthi: .byte 0
done: .byte 0
runs_left: .byte 0
pairs_left: .byte 0
schedule_lo: .byte 0
schedule_hi: .byte 0
schedule_index: .byte 0
image_end:

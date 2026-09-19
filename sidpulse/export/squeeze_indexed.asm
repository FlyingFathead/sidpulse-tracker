; SQUEEZER v2.0.2 resident phrase-call decoder. One non-recursive call level.
; Tags $10..$7f: dictionary entry (literal block or one-shot phrase).
; Inline literal lengths are 1..15. References and repeated calls are unchanged.
; Tag 0: repeat-count, phrase address LE16. Tag $80: return. Count is 1..255.
; Build at PLAYER_LOAD=$1000 (PSID) or $09b4 (compact PRG), STREAMS=1/5/26.
; Two JMP entry points; start words and loop flag immediately follow them.
; State is inside this image; only $f8/$f9 and at most 4 stack bytes are used.
; Reads packed literals in place. NO decompression buffer or reference recursion.
; Normal calls always return. The host compiler checks a conservative cycle cap.
* = PLAYER_LOAD
        jmp init
        jmp play
starts: .fill STREAMS*2,0
loop_song: .byte 1
dictionary_length: .fill 112,0
dictionary_lo: .fill 112,0
dictionary_hi: .fill 112,0
init:
        cld
        lda #0
        sta done
        sta silent_left
        sta ticks_left
        sta lastlo
        sta lasthi
        ldx #24
clear_sid:
        sta $d400,x
        dex
        bpl clear_sid
        jsr reset_readers
        jmp decode
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
        lda silent_left
        beq decode
        dec silent_left
        jmp tick_done
decode:
        ldx #STREAMS-1
        jsr getbyte
.if STREAMS != 5
        cmp #26
        bcs special
        cmp #25
        beq single_gap
        sta register_offset
.if STREAMS == 26
        tax
.else
        ldx #0
.endif
        jsr getbyte
        ldx register_offset
        sta $d400,x
        jmp decode
single_gap:
        jsr gap
        jmp decode
special:
        sec
        sbc #26
.endif
        cmp #0
        beq tick_done
        cmp #1
        beq end_song
        cmp #2
        bne not_timer
        jmp set_timer
not_timer:
        cmp #3
        beq silent_run
.if STREAMS == 5
        sta command
        and #3
        sta voice
        tax
        lda bases,x
        sta voice_base
        lda command
        lsr
        lsr
        sta run_left
next_event:
        ldx voice
        jsr getbyte
        cmp #7
        beq lane_gap
        clc
        adc voice_base
        sta register_offset
        ldx voice
        jsr getbyte
        ldx register_offset
        sta $d400,x
consumed:
        dec run_left
        bne next_event
        jmp decode
lane_gap:
        jsr gap
        jmp consumed
.endif
tick_done:
        lda idle_each
        sta ticks_left
        rts
silent_run:
        ldx #STREAMS-1
        jsr getbyte
        sta silent_left
        dec silent_left
        jmp tick_done
end_song:
        lda loop_song
        beq stop
        jsr reset_readers
        jmp decode
stop:
        lda #0
        sta $d404
        sta $d40b
        sta $d412
        inc done
        rts
set_timer:
        ldx #STREAMS-1
        jsr getbyte
        sta newlo
        jsr getbyte
        sta newhi
        jsr getbyte
        sta idle_each
        lda newlo
        cmp lastlo
        bne changed_timer
        lda newhi
        cmp lasthi
        bne changed_timer
        jmp decode
changed_timer:
        lda newlo
        sta lastlo
        sta $dc04
        lda newhi
        sta lasthi
        sta $dc05
        lda $dc0e
        ora #$11
        sta $dc0e
        jmp decode
gap:
        ldx #6
wait_gate:
        dex
        bne wait_gate
        rts
reset_readers:
        ldx #STREAMS-1
reset_one:
        lda #0
        sta left,x
        sta repeats_left,x
        txa
        asl
        tay
        lda starts,y
        sta sequence_lo,x
        lda starts+1,y
        sta sequence_hi,x
        dex
        bpl reset_one
        rts
; Read one decoded byte from stream X, preserving X. Y/A/flags are scratch.
; Inline lengths are 1..15; reference lengths are 1..127.
getbyte:
        lda left,x
        bne ready
load_packet:
        lda sequence_lo,x
        sta $f8
        lda sequence_hi,x
        sta $f9
        ldy #0
        lda ($f8),y
        bmi reference
        bne positive_packet
        jmp phrase_call
positive_packet:
        cmp #16
        bcc literal_packet
        jmp indexed_packet
literal_packet:
        sta left,x
        clc
        lda sequence_lo,x
        adc #1
        sta source_lo,x
        lda sequence_hi,x
        adc #0
        sta source_hi,x
        clc
        lda source_lo,x
        adc left,x
        sta sequence_lo,x
        lda source_hi,x
        adc #0
        sta sequence_hi,x
        jmp ready
reference:
        and #127
        bne normal_reference
        jmp phrase_boundary
normal_reference:
        sta left,x
        iny
        lda ($f8),y
        sta source_lo,x
        iny
        lda ($f8),y
        sta source_hi,x
        clc
        lda sequence_lo,x
        adc #3
        sta sequence_lo,x
        bcc ready
        inc sequence_hi,x
ready:
        lda source_lo,x
        sta $f8
        lda source_hi,x
        sta $f9
        ldy #0
        lda ($f8),y
        inc source_lo,x
        bne no_carry
        inc source_hi,x
no_carry:
        dec left,x
        rts
indexed_packet:
        sec
        sbc #16
        tay
        lda dictionary_length,y
        beq indexed_phrase
        sta left,x
        lda dictionary_lo,y
        sta source_lo,x
        lda dictionary_hi,y
        sta source_hi,x
        inc sequence_lo,x
        bne indexed_ready
        inc sequence_hi,x
indexed_ready:
        jmp ready
indexed_phrase:
        lda sequence_lo,x
        sta return_lo,x
        lda sequence_hi,x
        sta return_hi,x
        lda #1
        sta repeats_left,x
        lda dictionary_lo,y
        sta sequence_lo,x
        lda dictionary_hi,y
        sta sequence_hi,x
        jmp load_packet
; Calls are parser state, never recursive CPU-stack calls. Phrase bodies contain
; ordinary or indexed literal/reference packets. A repeated body restarts in place.
phrase_call:
        lda sequence_lo,x
        sta return_lo,x
        lda sequence_hi,x
        sta return_hi,x
        ldy #1
        lda ($f8),y
        sta repeats_left,x
phrase_start:
        ldy #2
        lda ($f8),y
        sta sequence_lo,x
        iny
        lda ($f8),y
        sta sequence_hi,x
        jmp load_packet
phrase_boundary:
        lda return_lo,x
        sta $f8
        lda return_hi,x
        sta $f9
        dec repeats_left,x
        bne phrase_start
        ldy #0
        lda ($f8),y
        beq long_return
        lda #1
        bne advance_return
long_return:
        lda #4
advance_return:
        clc
        adc return_lo,x
        sta sequence_lo,x
        lda return_hi,x
        adc #0
        sta sequence_hi,x
        jmp load_packet
; Mutable state (already part of the measured resident player image).
sequence_lo: .fill STREAMS,0
sequence_hi: .fill STREAMS,0
source_lo: .fill STREAMS,0
source_hi: .fill STREAMS,0
left: .fill STREAMS,0
repeats_left: .fill STREAMS,0
return_lo: .fill STREAMS,0
return_hi: .fill STREAMS,0
done: .byte 0
ticks_left: .byte 0
idle_each: .byte 0
silent_left: .byte 0
lastlo: .byte 0
lasthi: .byte 0
newlo: .byte 0
newhi: .byte 0
register_offset: .byte 0
.if STREAMS == 5
command: .byte 0
voice: .byte 0
voice_base: .byte 0
run_left: .byte 0
bases: .byte 0,7,14,21
.endif

image_end:

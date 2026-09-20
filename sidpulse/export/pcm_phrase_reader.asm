; PCM adapter of the existing SQUEEZER v2.0.1/v2.0.2 readers.
; NMI uses no X/Y/ZP or reader state, so packet decoding may be interrupted.
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
.if DECODER == 202
        cmp #16
        bcc literal_packet
        jmp indexed_packet
.endif
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
.if DECODER == 202
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
.endif
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
.if DECODER == 202
        ldy #0
        lda ($f8),y
        beq long_return
        lda #1
        bne advance_return
long_return:
.endif
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

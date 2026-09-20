; SIDpulse experimental mixed SID / waveform-DAC PCM player.
; Owns CIA1 TA (music, polled), CIA2 TA (PCM NMI), CH3 and $f8/$f9.
; CH1/2 remain SID. Display/sprites are off for deterministic DAC timing.
; ROM is out, I/O in. NMI uses A only and preserves P; no shared ZP.
; Build: scripts/build_pcm_player.py. Ordinary exports use the bundled image.
STREAMS = 28
; DECODER from the build script: 1=literal, 201=phrase calls, 202=dictionary IDs.
* = $0801
        .word basic_end
        .word 10
        .byte $9e
        .text "2061"
        .byte 0
basic_end: .word 0
entry:
        php
        sei
        cld
        lda $01
        sta saved_port
        lda $f8
        sta saved_zp
        lda $f9
        sta saved_zp+1
        lda rsid_mode
        bne boot
        lda #<banner
        sta $f8
        lda #>banner
        sta $f9
        ldy #0
print:
        lda ($f8),y
        beq printed
        jsr $ffd2
        iny
        bne print
printed:
        lda $02a6
        cmp target_pal
        beq boot
        jmp return_basic
boot:
        lda #$7f
        sta $dc0d
        sta $dd0d
        lda #0
        sta $dc0e
        sta $dd0e
        sta $dd0f
        lda $dc0d
        lda $dd0d
        lda #$35
        sta $01
        lda $d011
        sta saved_display
        lda $d015
        sta saved_sprites
        lda $d011
        and #$ef
        sta $d011
        lda #0
        sta $d015
wait_vblank:
        bit $d011
        bpl wait_vblank
wait_frame:
        bit $d011
        bmi wait_frame
        lda #<nmi
        sta $fffa
        lda #>nmi
        sta $fffb
        lda #<irq
        sta $fffe
        lda #>irq
        sta $ffff
        lda #0
        sta $dc03
        lda #$ff
        sta $dc02
        jsr prime_sid
        jsr init
wait_tick:
        lda rsid_mode
        bne check_timer
        lda #$7f
        sta $dc00
        lda $dc01
        and #$80
        beq exit_music
check_timer:
        lda $dc0d
        and #1
        beq wait_tick
        jsr play
        jmp wait_tick
exit_music:
        jsr pcm_stop
        lda #0
        sta $dc0e
        ldx #24
silence:
        sta $d400,x
        dex
        bpl silence
        lda saved_display
        sta $d011
        lda saved_sprites
        sta $d015
        lda saved_port
        sta $01
        jsr $ff84
        jsr $ff81
return_basic:
        lda saved_zp
        sta $f8
        lda saved_zp+1
        sta $f9
        plp
        rts
irq:    rti
saved_port: .byte $37
saved_display: .byte $1b
saved_sprites: .byte 0
saved_zp: .word 0
initial_volume: .byte $1f
fade_mode: .byte 0
fade_level: .byte 0
; Establish mixer DC before musical time, without a full-volume step.
prime_sid:
        lda #0
        ldx #23
prime_clear:
        sta $d400,x
        dex
        bpl prime_clear
        lda initial_volume
        and #$f0
        sta fade_mode
        lda initial_volume
        and #15
        sta fade_level
        ldx #0
prime_step:
        txa
        ora fade_mode
        sta $d418
        lda #8
prime_wait:
        ldy #0
prime_delay:
        dey
        bne prime_delay
        sec
        sbc #1
        bne prime_wait
        cpx fade_level
        beq prime_done
        inx
        bne prime_step
prime_done:
        rts
target_pal: .byte 1
rsid_mode: .byte 0
banner: .byte 147,142
        .text "SIDPULSE PCM-ENHANCED (EXPERIMENTAL)",13
        .text "CH1/2 SID + CH3 WAVEFORM DAC",13
        .text "TRACKER CH"
source_channel_text: .text "3"
        .text " -> C64 CH3 DIGI",13
        .text "RUN/STOP TO EXIT. MATCH PAL/NTSC + SID.",13,0
        .fill $1000-*,0
        jmp init
        jmp play
starts: .fill STREAMS*2,0
loop_song: .byte 1
sample_period: .word 245
primed: .byte 0
owned: .byte 0
neutral_level: .byte 91
.if DECODER == 202
dictionary_length: .fill 112,0
dictionary_lo: .fill 112,0
dictionary_hi: .fill 112,0
.endif
init:
        cld
        lda #0
        sta active
        sta owned
        sta done
        sta ticks_left
        sta volume
        sta mode
        sta lastlo
        sta lasthi
        ldx #23              ; retain the mixer level established before init
clear_sid:
        sta $d400,x
        dex
        bpl clear_sid
        jsr reset_readers
        jmp decode
play:
        cld
        lda done
        bne play_done
        lda ticks_left
        beq decode
        dec ticks_left
play_done:
        rts
decode:
        ldx #27
        jsr getbyte
        cmp #25
        bcs special
        sta register_offset
        tax
        jsr getbyte
        ldx register_offset
        cpx #24
        bne write_sid
        sta volume
        ldx owned
        beq normal_volume
        and #$7f             ; keep CH3 audible until the SID handoff
normal_volume:
        ldx #24
write_sid:
        sta $d400,x
        jmp decode
special:
        cmp #25
        bne not_gap
        jsr gap
        jmp decode
not_gap:
        cmp #26
        bne not_tick
        lda idle_each
        sta ticks_left
        rts
not_tick:
        cmp #27
        bne not_end
        jsr pcm_stop
        lda loop_song
        beq stop_song
        jsr reset_readers
        jmp decode
stop_song:
        lda #0
        sta $d404
        sta $d40b
        sta $d412
        inc done
        rts
not_end:
        cmp #28
        bne not_timer
        ldx #27
        jsr getbyte
        sta newlo
        jsr getbyte
        sta newhi
        jsr getbyte
        sta idle_each
        lda newlo
        cmp lastlo
        bne timer_changed
        lda newhi
        cmp lasthi
        bne timer_changed
        jmp decode
timer_changed:
        lda newlo
        sta lastlo
        sta $dc04
        lda newhi
        sta lasthi
        sta $dc05
        lda #$11
        sta $dc0e
        jmp decode
not_timer:
        cmp #30
        bne stop_command
        jsr pcm_start
        jmp decode
stop_command:
        jsr pcm_stop
        jmp decode
gap:
        ldx #6
wait_gate:
        dex
        bne wait_gate
        rts
pcm_start:
        jsr stop_timer
        ldx #25
        jsr getbyte
        sta descriptor_lo
        ldx #26
        jsr getbyte
        sta $f9
        lda descriptor_lo
        sta $f8
        ldy #0
        lda ($f8),y
        sta sample_read+1
        iny
        lda ($f8),y
        sta sample_read+2
        iny
        lda ($f8),y
        sta count_lo
        iny
        lda ($f8),y
        sta count_hi
        lda #0
        sta primed
        lda owned
        beq warm_midpoint
        jmp midpoint_ready
warm_midpoint:
        ; Latch this model's silent DAC level before opening PCM. The ramp
        ; lasts exactly the same number of clocks as between sample NMIs.
        lda #$08
        sta $d412
        lda #0
        sta $d40e
        sta $d413
        lda #$f0
        sta $d414
        lda neutral_level
        sta $d40f
        lda #$00             ; keep GATE closed until the silent value is held
        sta $d412
midpoint_delay:
        bpl midpoint_sled     ; patched: skip 5 NOPs PAL, 0 NTSC
midpoint_sled:
        .rept 110
        nop
        .endrept
        bpl midpoint_capture
midpoint_capture:
        lda #$10
        sta $d412
midpoint_ready:
        lda #$09
        sta $d412             ; hold the DAC while resetting the oscillator
        lda #1
        sta owned
        lda volume
        and #$7f
        sta $d418
        lda sample_period
        sta $dd04
        lda sample_period+1
        sta $dd05
        lda $dd0d
        lda #1
        sta active
        lda #$81
        sta $dd0d
        lda #$11
        sta $dd0e
        rts
pcm_stop:
        jsr stop_timer
        lda owned
        beq pcm_stopped
        lda #0
        sta owned
        lda #$08
        sta $d412
        lda volume
        sta $d418
pcm_stopped:
        rts
stop_timer:
        lda #0
        sta active           ; before every descriptor/pointer mutation
        sta $dd0e
        lda #$7f
        sta $dd0d
        lda $dd0d
        rts
; NMI entry + exit preserves A and P; no X/Y/ZP touched and no JSR.
nmi:
        pha
        lda $dd0d
        and #1
        beq nmi_done          ; RESTORE or other non-timer NMI
        lda active
        beq nmi_done
        lda $dd04
        eor #$ff
        lsr
        bcc parity_ready
parity_ready:
        sec
stabilize_sub:
        sbc #16
        and #7
        sta delay_branch+1
delay_branch:
        bpl delay_sled
delay_sled:
        .rept 8
        nop
        .endrept
        lda primed
        bne capture_dac
        inc primed
        jmp reset_dac
capture_dac:
        lda #$11
        sta $d412
reset_dac:
        lda #$09
        sta $d412
sample_read:
        lda $ffff
        cmp #$ff
        beq nmi_end
        sta $d40f
        lda #$01
        sta $d412
        inc sample_read+1
        bne pointer_ready
        inc sample_read+2
pointer_ready:

nmi_done:
        pla
        rti
nmi_end:
        ; The preceding sample is the silent midpoint. Hold it between hits;
        ; re-opening the envelope or changing master volume would click.
        lda #0
        sta active
        sta $dd0e
        lda #$7f
        sta $dd0d
        jmp nmi_done
reset_readers:
        ldx #STREAMS-1
reset_one:
        lda #0
        sta left,x
.if DECODER >= 201
        sta repeats_left,x
.endif
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
.if DECODER == 1
; Resident literal/reference stream decoder, identical packet ABI to v1.
getbyte:
        lda left,x
        bne ready
        lda sequence_lo,x
        sta $f8
        lda sequence_hi,x
        sta $f9
        ldy #0
        lda ($f8),y
        bmi reference
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
sequence_lo: .fill STREAMS,0
sequence_hi: .fill STREAMS,0
source_lo: .fill STREAMS,0
source_hi: .fill STREAMS,0
left: .fill STREAMS,0
.else
        .include "pcm_phrase_reader.asm"
.endif
done: .byte 0
ticks_left: .byte 0
idle_each: .byte 0
lastlo: .byte 0
lasthi: .byte 0
newlo: .byte 0
newhi: .byte 0
register_offset: .byte 0
descriptor_lo: .byte 0
active: .byte 0
count_lo: .byte 0
count_hi: .byte 0
phase: .byte 0
held: .byte 0
volume: .byte 0
mode: .byte 0
code_end:
        .fill $1800-*,0
image_end:

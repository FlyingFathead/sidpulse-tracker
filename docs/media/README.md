# Playback preview

`sidpulse-f5-playback.gif` and the H.264/AAC MP4 show eight seconds of actual
SIDpulse Tracker 0.2.30 F5 song playback. Source: the bundled
`examples/autumn-at-five.sidpulse`, unchanged. The native audio subprocess ran
with SDL dummy audio/video drivers; the capture includes all three voice scopes
and the control/filter channel. No synthetic waveforms were substituted.
The MP4 soundtrack is rendered from the same song through the native sequencer,
reSIDfp and host output conditioner, trimmed to the first captured frame's
published playback position. It is mono, 48 kHz AAC; UI telemetry is buffered,
so this is a promotional preview, not a sample-exact audiovisual timing test.
The GIF is silent, with a **Watch with audio** MP4 link immediately below it.

MP4: 960×720, 20 fps, 160 frames. GIF: 960×720, 12.5 fps, looping.
The animation appears directly below the main README logo. These are static
repository media files; the application never loads or records them at runtime.
Capture ran separately from performance measurements. See
`validation/v0.2.30/promo-capture.json` for source and output hashes.

## Complete Autumn at Five playthrough

`sidpulse-f5-playback-full.mp4` contains the entire first song pass: 96 seconds,
3,072 musical ticks, 1,920 frames at 20 fps, 960×720 H.264 video and mono
48 kHz AAC audio. The README points to this complete version; its inline GIF
remains the short eight-second preview above. The original short MP4 remains
available as an optional clip.

The full capture uses actual F5 native playback and voice scopes. Video frames
follow published sequencer time; audio is rerendered from sample zero through
the first loop boundary using the same native sequencer, reSIDfp and output
conditioner. Buffered telemetry can differ slightly from audio time. The
source song is unchanged, and every song order is present in the capture.
`validation/v0.2.30/promo-full-capture.json` records duration, codecs and hashes.
Capture/encoding ran after the performance trials. These are repository assets
and add no tracker runtime work.

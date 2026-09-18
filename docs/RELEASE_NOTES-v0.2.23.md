# SIDpulse Tracker v0.2.23 - output devices and test arpeggio

Alt+F12 now lets you choose an SDL audio output, preview it with a short C-E-G-C
arpeggio, refresh the device list and reset the audio defaults.

The selected output is saved in machine preferences after a successful apply.
System default is represented by `audio_output_device: null`. Reset defaults
stages System default, 2048 samples and underrun detection enabled; OK saves.
Cancel leaves preferences unchanged. Missing saved devices fall back to default.

The test temporarily holds song playback, preserving native SID state, queued
music and pause state, then restores the original output. It does not edit the
song, change saved mute/solo settings or save the preview selection.

The 0.2.22 isolated audio process, native sound path, dependency pins, project
format 6 and exporter/player binaries remain unchanged. Performance comparisons,
regression evidence and platform limitations are documented in
[validation](https://github.com/FlyingFathead/sidpulse-tracker/blob/v0.2.23/docs/VALIDATION-v0.2.23.md).
Linux SDL dummy checks do not constitute native Windows or physical-device testing.

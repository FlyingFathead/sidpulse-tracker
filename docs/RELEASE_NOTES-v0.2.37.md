# v0.2.37 — playback navigation and reference drum presets

The file browser now keeps keyboard/wheel selection centered, clamping at the
first and last entries. Mouse selection stays under the pointer for a second
click; dragging the scrollbar still scrolls manually.

On the F5 Info page, minus/plus and keypad minus/plus visit the previous/next
song order at row zero. The header includes equivalent triangle buttons beside
the playback position. Controls clamp at either end and are inactive while
stopped/paused or looping a pattern. Rapid presses resolve in the audio worker.
The next tick uses the existing sample clock and order-transition path, retaining
voice state and instrument memory. It does not reset the device, warm up another
chip, or change normal song rendering. Destination notes and effects still run.
An active automation take finishes before navigation.

F4's built-in catalog adds **[Wavetable] Drums & Percussion**, containing the
exact frozen kick/snare recipes from the v0.2.36 reference example and MP3s.
They are ordinary SID instruments, work without embedded samples, and load only
when the catalog opens. The fitter, sample sources and reference project are
unchanged. The category sidebar fits the additional category on small windows.

Windows CI previously ran FFmpeg-dependent tests without installing FFmpeg.
The workflow now installs it with Chocolatey, passes its executable through
SIDPULSE_FFMPEG, and verifies it before running pytest on either operating system.
The 13 reported failures and an additional MP3 decode check pass locally with
FFmpeg. A new Windows Actions run is still needed to verify the runner itself.
No media tests have been skipped to hide the dependency.

All four SQUEEZER versions, including v2.0.1 and default v2.0.2, and both DIGI
methods remain available. The default audio buffer is still 2048 samples; 512
remains a stress setting. See [performance](PERFORMANCE-v0.2.37.md),
[validation](VALIDATION-v0.2.37.md), [keyboard details](KEYBOARD_MAPPING.md), and
[update instructions](APPLY-v0.2.37.md).

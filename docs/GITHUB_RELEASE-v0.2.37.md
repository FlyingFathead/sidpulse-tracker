# SIDpulse Tracker v0.2.37

- **Playback navigation:** use minus/plus on the F5 Info page or the header's
  triangle buttons to visit the previous/next song order, without restarting
  the audio device or resetting the sample clock.
- **Centered file browser:** keyboard/wheel selection follows the middle of
  the list and clamps at either end; mouse double-click targeting stays stable.
- **Wavetable drum presets:** the exact frozen reference kick and snare are now
  in F4 under **[Wavetable] Drums & Percussion**.
- **Windows CI:** install and verify FFmpeg before running the media tests.

124 focused tests passed locally. The performance audit contains 184 serial
measurements against v0.2.36; the updated build lost no audio frames in its
58 live trials. A PCM CPU spike did not recur in longer repeat measurements.
The 2048-sample default and 512-sample stress setting are preserved. Linux
SDL-dummy results do not certify every physical device or operating system.

All four SQUEEZER versions, including v2.0.1 and default v2.0.2, and both DIGI
methods remain available. The sample fitter, reference drum recipes and source
samples are unchanged from v0.2.36.

Use the **full ZIP** for a fresh installation, or the **incremental ZIP** over
v0.2.36. Both extract under `sidpulse-tracker/`. Verify the supplied SHA-256
checksums and run `python3 scripts/finish_update.py` after an incremental update.

[Installation](https://github.com/FlyingFathead/sidpulse-tracker/blob/v0.2.37/docs/APPLY-v0.2.37.md) ·
[Release details](https://github.com/FlyingFathead/sidpulse-tracker/blob/v0.2.37/docs/RELEASE_NOTES-v0.2.37.md) ·
[Performance and retained outliers](https://github.com/FlyingFathead/sidpulse-tracker/blob/v0.2.37/docs/PERFORMANCE-v0.2.37.md) ·
[Validation](https://github.com/FlyingFathead/sidpulse-tracker/blob/v0.2.37/docs/VALIDATION-v0.2.37.md)

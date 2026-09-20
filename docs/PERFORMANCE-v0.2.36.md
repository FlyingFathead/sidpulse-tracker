# Runtime performance: v0.2.36 against v0.2.35

198 serial trials cover three repetitions in alternating version order: a
174-trial full pass followed by 24 matched export trials after the compiler
priority change. The export table uses those follow-up trials. The
baseline is the supplied, unchanged v0.2.35 snapshot. Inputs and settings match
between releases. No tests, builds, emulators or archive creation ran alongside
measurement. CPU percentages below are percentages of one logical core;
UI and audio are separate processes. These are Linux SDL-dummy measurements,
not a physical sound-device or C64 certification.

Environment: Python 3.12.14, Linux x86_64, numpy 2.3.5, pygame-ce 2.5.7, pyresidfp 0.17.0.
Two allowed CPUs are used for live trials; one for offline/render trials.
Raw results and input hashes are under `docs/validation/v0.2.36/runtime/`.

## What changed

- Stopped audio no longer emulates and conditions endless silent blocks.
  It keeps the SDL queue ready and wakes on commands. Held sustained notes,
  unfinished samples and conservative full-envelope release times stay active.
  Completed one-shot sample and gated instrument previews can become idle.
- A quiet window redraws at 5 Hz. Input and services still poll at 60 Hz,
  with immediate redraw for input, playback, active jobs and dragging.
- Meter calculations use the existing NumPy dependency. PCM is untouched;
  scalar-reference tests cover peak, RMS and waveform display equivalence.
- Spawned export compilers run at lower priority on POSIX, as fitting already
  did. This protects foreground scheduling under contention; it does not cap
  export CPU use or change compilation results. Windows scheduling is unchanged.
- Active SID synthesis, scopes, musical sequencing, conditioning and C64
  encoding retain their existing algorithms. The 2048-sample default stays;
  512 samples is the stress setting.

## Live application

Medians across three runs; gap and late-callback columns show
counts across all three runs. Normal cases measure five seconds after warmup;
fitting cases measure eighteen seconds. Info-page cases retain all scopes.
Pattern/sample-bank cases use their normal page behavior. Recording uses the
modal over Info so scopes remain visible. Cursor movement exercises input
during playback; recording exercises continuous channel automation.

| Case | Buffer | UI CPU old → new | Audio CPU old → new | Gaps old/new | Late callbacks old/new |
|---|---:|---:|---:|---:|---:|
| playback / sid / info | 2048 | 17.42% → 19.14% | 20.11% → 20.37% | 0/0 | 1/8 |
| playback / sid / info | 512 | 17.18% → 17.41% | 22.38% → 23.22% | 0/0 | 0/7 |
| playback / pcm / info | 2048 | 17.58% → 17.37% | 20.48% → 19.91% | 0/0 | 0/0 |
| playback / pcm / info | 512 | 18.00% → 18.35% | 23.39% → 24.33% | 4/0 | 62/4 |
| startup / sid / pattern | 2048 | 20.64% → 2.69% | 9.50% → 1.24% | 0/0 | 0/0 |
| stopped / sid / info | 2048 | 16.76% → 2.66% | 17.79% → 1.24% | 0/0 | 0/0 |
| paused / sid / info | 2048 | 16.57% → 2.69% | 3.52% → 1.04% | 0/0 | 0/0 |
| audition / sid / info | 2048 | 16.81% → 16.99% | 18.47% → 18.47% | 0/0 | 0/0 |
| sample / sid / samples | 2048 | 11.37% → 10.36% | 10.76% → 9.11% | 0/0 | 0/0 |
| edit / sid / pattern | 2048 | 20.73% → 22.18% | 11.40% → 11.82% | 0/0 | 0/0 |
| record / sid / info | 2048 | 32.71% → 25.25% | 27.52% → 20.94% | 0/0 | 4/0 |
| fit / pcm / info | 2048 | 27.06% → 22.42% | 21.40% → 21.28% | 0/0 | 0/2 |
| fit / pcm / info | 512 | 26.69% → 21.71% | 23.89% → 23.39% | 0/0 | 16/4 |
| export / sid / info | 2048 | 37.24% → 35.69% | 20.46% → 19.47% | 0/0 | 5/0 |
| export / sid / info | 512 | 38.43% → 37.77% | 23.31% → 24.22% | 0/7 | 14/91 |
| export / pcm / info | 2048 | 39.83% → 42.25% | 19.81% → 20.83% | 0/0 | 0/3 |
| export / pcm / info | 512 | 40.82% → 39.46% | 23.04% → 22.15% | 4/0 | 37/1 |

Export rows measure the busy comparison window, then cancel any unfinished
analysis when the trial closes. They are contention/cancellation measurements,
not full-song compile-time measurements. Separate validation compiles the
delivered drum project to PSID and PRG with all four SQUEEZER versions.
Fitting leaves the playing arrangement unchanged; its proposal is not applied.

## Offline audio pipeline

Each trial renders twelve seconds, with scopes, conditioning and metering.
Values are median CPU milliseconds per block. Smaller values are better.

| Input | Buffer | Old | New | Change |
|---|---:|---:|---:|---:|
| sid | 2048 | 6.733 | 6.254 | -7.1% |
| sid | 512 | 1.709 | 1.717 | +0.4% |
| pcm | 2048 | 6.501 | 6.361 | -2.2% |
| pcm | 512 | 1.751 | 1.776 | +1.4% |

## UI draw cost

200 complete frames per trial, with identical visible content. This isolates
drawing cost from the idle redraw scheduler. Values are CPU milliseconds/frame.

| Page | Window | Old | New | Change |
|---|---:|---:|---:|---:|
| pattern | 640×480 | 0.951 | 0.973 | +2.3% |
| info | 640×480 | 0.926 | 0.929 | +0.3% |
| samples | 640×480 | 0.765 | 0.756 | -1.1% |
| instrument | 640×480 | 0.828 | 0.862 | +4.2% |
| pattern | 1280×900 | 2.675 | 2.665 | -0.4% |
| info | 1280×900 | 2.054 | 2.080 | +1.3% |
| samples | 1280×900 | 1.554 | 1.565 | +0.7% |
| instrument | 1280×900 | 2.082 | 2.081 | -0.0% |

## Interpretation, costs and remaining work

Stopped Info-page CPU (median of each run's UI + audio total) fell from
34.72% to 3.94% of one core; paused fell from 20.10% to 3.73%. The application's
startup Pattern-page total fell from 30.14% to 3.94%. These are measurements in
this environment, not a prediction of an identical percentage on every machine.
The sustained SID-audition audio median was unchanged at 18.47%.

The 2048-sample offline SID pipeline improved by 7.1%, and PCM by 2.2%.
The 512-sample measurements varied slightly upward (+0.4% SID, +1.4% PCM).
Some live CPU and late-callback measurements also rose. There is no claim
that every active mode became faster. Complete-frame drawing cost is broadly
similar; the large idle gain comes from doing fewer redundant frames.

Fitting uses more finite background computation: median worker CPU in the
2048-sample fitting trials increased from 2.47 to 11.08 seconds. The final
original-WAV reference fits took 12.78 seconds (kick) and 16.42 seconds (snare),
including 247 and 274 candidate renders respectively. The search has a
320-candidate limit. Lower average UI CPU in fitting trials is partly affected
by time spent in different progress/result dialogs; it should not be treated
as an isolated drawing optimization. Fit analysis adds no work to normal
playback after accepting the ordinary frozen SID instrument.

High CPU in a finite export job is expected. The acceptance concern is
contention with playback. In the initial broad pass the candidate had five
export-time underrun episodes totaling 4,096 missing frames: SID at 2048 and
512, plus PCM at 512. Those failed trials remain in `docs/validation/v0.2.36/runtime/runtime.jsonl`.
The old release had four episodes / 2,560 missing frames during one PCM
playback-at-512 trial. No candidate normal-playback or fitting trial recorded
missing frames. Late callbacks are separate measurements and are not hidden
when the queue has enough audio to avoid a gap.

A separate diagnostic profile found the export compiler using about one core.
Of 4.94 profiled seconds, checked song recording accounted for 3.59 seconds
cumulative, including restart preparation; deep copying accounted for 1.45
seconds cumulative. These nested values must not be added. The compiler now
requests POSIX niceness +5 in its spawned child, matching fitting's existing
policy. It can still occupy an otherwise available core. The main/UI process
priority is untouched. Windows behavior is unchanged and was not measured.
The compiler algorithms, SQUEEZER versions and exported bytes are preserved.

The 24-trial export follow-up recorded **zero missing frames at 2048** in both
versions. At 512, the candidate had one failed SID-export trial: seven gap
episodes / 4,096 missing frames (85.3 ms in total), with 91 late callbacks.
Its other five 512 export trials had no missing frames. The baseline had one
failed PCM-export trial: four episodes / 2,560 missing frames (53.3 ms total).
The candidate's affected trial also had elevated UI/audio/compiler CPU and
132 ms maximum drawing time; adjacent baseline trials slowed as well. This
suggests a scheduling/load outlier, but does not prove its cause or excuse it.
**512-sample export stress is not reliably gap-free in this environment.**
The priority change is best-effort scheduling, not a demonstrated complete
cure. Keep 2048 as the default; further real-device stress investigation remains.
All follow-up records are in `docs/validation/v0.2.36/runtime/export-runtime.jsonl`.

Further useful work should target measured costs: reducing redundant immutable
look-ahead copies in export and caching static modal drawing. Both require
output/UI equivalence checks. Native SID synthesis and the three separate
scope emulators remain substantial active costs; disabling scopes or reducing
synthesis quality is not counted as an optimization. Do not shorten envelope
release or skip musical frames to meet a CPU target.

Timing validation covers retained native gate-cycle samples, exact conditioner
PCM, callback starvation accounting, sustained notes, quiet PCM lead-ins,
completed one-shots, release activity on both SID models, and frozen transport
position across pause/resume. Linux dummy-device results cannot certify
physical-device scheduling, Windows audio, or real C64 playback.

## Reproduce and ongoing checks

```bash
python scripts/benchmark_runtime.py --baseline ../previous/sidpulse-tracker --candidate . --out ../runtime-results --repetitions 3
python scripts/benchmark_runtime.py --baseline ../previous/sidpulse-tracker --candidate . --out ../export-results --repetitions 3 --cases export
```

The runner uses immutable reference songs from the baseline and checks their
hashes afterwards. Keep the output directory outside the source tree. Record
material regressions and rerun/profile them before accepting a change. Compare
features enabled, never with scopes or sound quality silently disabled.
Use 2048 as the release default and 512 as the scheduling stress test. Further
hardware/device testing remains necessary for platform-specific latency.

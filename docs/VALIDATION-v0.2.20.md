# SIDpulse Tracker v0.2.20 — validation repair

Date: 2026-09-17. **Local source candidate; no commit, push, tag or release.**
Baseline: the previously supplied `sidpulse-tracker-v0.2.19-full.zip`, matching the
user-applied v0.2.19 update. Application version is 0.2.20; native format remains 6.

## Reported failure and diagnosis

The user's dependency-complete v0.2.19 run reported **946 passed, 5 failed**.
That is the user's supplied result, not a test run performed in this container.
Four parametrizations of `test_channel_py65.py` failed on an idle callback with
`ReplayCPU == 30` versus `py65 == 27` cycles. One program-editor integration test
still expected an `export` key belonging to the superseded export dialog.

The pinned **py65 1.2.0** source declares `DEC absolute` ($CE) with `cycles=3`.
MOS specifies **six cycles** for this absolute read-modify-write instruction.
The existing production verifier already charges six and remains unchanged.

Primary references checked for this repair:

- [py65 1.2.0 source, DEC absolute declaration](https://github.com/mnaberez/py65/blob/1.2.0/py65/devices/mpu6502.py#L1059-L1062).
- [MOS MCS6500 Hardware Manual, January 1976, Appendix A.4.2 transcription](https://xotmatrix.com/6502/6502-single-cycle-execution.html).

A local instruction trace of the shipped single-stream binary reproduced this
specific idle path after tick 1 of the test's interleaved fixture:

| PC | Instruction | Correct cycles |
|---|---|---:|
| $1003 | JMP absolute | 3 |
| $1029 | CLD | 2 |
| $102A | LDA absolute | 4 |
| $102D | BEQ taken, same page | 3 |
| $1030 | LDA absolute | 4 |
| $1033 | BEQ not taken | 2 |
| $1035 | DEC absolute | 6 |
| $1038 | RTS | 6 |
| **Total** | | **30** |

Using py65's incorrect three-cycle DEC entry gives exactly 27. The repair is
not an allowance for a three-cycle discrepancy: equality assertions remain exact.

## Changes

`tests/py65_nmos.py` subclasses the upstream CPU without replacing instruction
execution. It validates the known opcode metadata and copies the cycle table per
instance, correcting only $CE to six cycles. Both the known erroneous entry and
an already-correct six-cycle entry are supported; unexpected metadata aborts.
No site-packages files or shared class tables are changed. The adapter is used
by the SID, PRG, stream and channel CPU tests, not by the runtime application.

The program-editor integration test checks the actual `export_squeezer` dialog,
SID destination, successfully prepared export, default enabled state and source
copy. It retains the existing real native-save/SID-export steps and assertions.
The channel test retains exact cycle and ordered-write comparisons and adds CIA
control-register equality and better failure context.

New tests check DEC cycle counts against fixed manual-derived expectations,
all 256 input values, wraparound/sign/zero results, carry/decimal preservation,
indexed page crossing, the 30-cycle idle path and the test adapter's isolation
and fail-closed behavior. No assertion is skipped to accommodate a mismatch.

## Checks performed in this container

Python 3.13.5, dependency-light test selection:

```bash
python -m pytest -q -ra \
  tests/test_replay_cycles.py tests/test_channel_squeeze.py \
  tests/test_phrase_optimizer.py tests/test_player_build_metadata.py \
  tests/test_squeeze.py tests/test_incremental_update.py \
  tests/test_project.py tests/test_editor.py tests/test_py65_nmos.py \
  tests/test_channel_py65.py tests/test_squeeze_gui.py
```

**246 passed, 3 skipped in 53.70 seconds.** The skipped modules are
`test_py65_nmos.py` and `test_channel_py65.py` (py65 unavailable), and
`test_squeeze_gui.py` (pygame unavailable). This is **not a full-suite pass**.
The GUI integration repair and independent py65 adapter tests have not executed
here. Do not combine this count with the user's baseline count or call the
skips passes. An earlier invocation was interrupted by the tool time limit;
the result above is the subsequent complete, successful run.

Dependency installation was attempted in an isolated virtual environment with
the project-pinned pygame-ce, pyresidfp and py65 versions. It failed at package
index access with unavailable DNS/network. No imitation pygame/py65 module was
substituted for the missing packages.

The existing benchmark was rerun for all four PAL/NTSC example projects and both
SID/PRG formats. All **16 output hashes** (squeezed and legacy for eight
song/format pairs), size/RAM figures and deterministic replay report fields match
the v0.2.19 measurements exactly. Only report version and compile wall times
change. No source song was changed. Results are in the accompanying
`sidpulse-tracker-v0.2.20-measurements.json`.

All C64 `.bin` and assembly files, export compiler/optimizer/verifier sources,
GUI implementation, sequencer and bundled songs are byte-identical to v0.2.19.
Within runtime Python, only the application version declaration changes. Package
metadata changes only the version; dependencies and options stay unchanged.

Python syntax compilation and Git whitespace checks passed. The packaged update
was checked against a fresh v0.2.19 extraction, including check-only behavior,
backups, full target equality, repeat application, CRLF input, unknown-edit
refusal and preservation of unrelated files. The full source ZIP omits font
binaries, environments, caches and private project context.

## Remaining release gate

Run the complete suite in the existing project virtual environment:

```bash
./.venv/bin/python -m pytest -q -ra
```

The user's environment already had py65 and pygame available. Do not reinstall
or edit those packages to apply this fix. Their unchanged upstream code remains
the independent instruction implementation used by the corrected test adapter.

The repaired five tests and new native adapter tests must pass there before
claiming a dependency-complete result. Native headless smoke, actual audio,
64tass rebuilding, Windows, VICE and real-hardware validation remain separate
release gates as described in VALIDATION.md. No new audible-equivalence claim
is made; the exported binaries themselves are unchanged.

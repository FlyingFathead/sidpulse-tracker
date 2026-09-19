# SIDpulse Tracker v0.2.28 validation

This version gives the previously tested revised v0.2.27 a distinct identity.
The pre-bump full suite remains **1,375 passing tests**. It was not rerun for the
version-only change. All runtime files match that build except `__version__`.

**15 version-dependent tests passed** in 0.32 seconds: native save version stamps,
newer-version compatibility warnings/preservation, and both PRG wrappers with
both squeezer versions, startup credits and wrong-clock exits. Logs are under
`validation/v0.2.28/`. Earlier complete validation is retained in
[VALIDATION-v0.2.27.md](VALIDATION-v0.2.27.md).

The runtime version, VERSION file and pyproject metadata all report 0.2.28.
Both launchers obtain their banner from VERSION. New native saves and squeezed
PRG credits use the runtime constant. Native format versions remain unchanged.

A serial 24-record matched performance check covers pattern/instrument/recording
UI and native audio with default features enabled. See
[PERFORMANCE-v0.2.28.md](PERFORMANCE-v0.2.28.md); existing full-song PCM and all
four bundled example SID/PRG comparisons remain valid for identical code.

Full and incremental archives use distinct v0.2.28 filenames and the common
`sidpulse-tracker/` root. The incremental supports v0.2.26 and all delivered
v0.2.27 candidates. Packaging checks exact overlay/full equality, integrity,
version consistency, privacy, run.sh permissions and direct launcher smoke runs.

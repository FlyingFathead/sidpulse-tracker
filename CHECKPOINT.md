# SIDpulse Tracker v0.2.30 checkpoint

- Tracker 0.2.30 / SQUEEZER v2.0.2; native formats remain 6/7. Existing saves,
  native synthesis, recording and editing semantics remain unchanged.
- v2.0.2 adds one-byte dictionary IDs for frequent immutable blocks and
  single-execution phrase calls. Repeated calls and shared suffixes remain.
  The 336-byte dictionary and decoder are included in full resident costs.
- v8 gains another 1,245 bytes beyond v2.0.1; register packet data shrinks
  1,665 bytes and player grows 420 bytes. SID maximum cycles rise 8,172 to
  8,287. All earlier candidate families remain selectable and eligible.
- Four-version analysis shows all versions by default; saved Top 3 remains optional.
  `export_show_all_versions` defaults true and saves immediately on checkbox changes.
  Shared overflow scrollbars are integrated across the UI. Minima, complete ties,
  current-choice preservation, measured CPU, immediate selection, config and
  cancellation remain supported. No compilation occurs during drawing.
- v1.0/v2.0/v2.0.1 optimizer sources and player binaries are unchanged. Six new
  players use existing mutable state with no new per-stream fields or buffer.
- Independent 6502 tests cover every call's cycles, ordered SID/CIA writes,
  loop/stop/reinit, decimal flag, workspace and dictionary immutability.
- Serial export and native performance evidence is under validation/v0.2.30.
  All four bundled examples and unchanged native v8 are used. Native baseline
  is immutable v0.2.29 (e4e38c1); M/S and scopes stay enabled.
- GoatTracker 2.77 source and the supplied Luxocrates explanation of Hubbard's
  player were studied for concepts. Acknowledgments and findings are in docs.
  No third-party code, transcript or song data was incorporated.
- Exact arithmetic-packet prototype was rejected: one-byte saving on the best
  stress layout did not pay for the decoder. It is not in the shipped runtime.
- Supplied SP window icon loads once before window creation; optional Linux
  desktop integration is documented. README GIF/MP4 captures actual F5 playback
  of bundled Autumn at Five, with all three scopes and no source mutation.
  The full MP4 covers one complete 96-second pass with audio; the GIF stays short.
  README official-source notice is immediately below the logo.
- Full and incremental archives retain executable run.sh and common root;
  final-named cumulative overlay supports v0.2.26 through the earlier v0.2.30.
  No remote push, tag or publication.

See docs/SQUEEZER-v2.0.2.md, docs/PERFORMANCE-v0.2.30.md,
docs/VALIDATION-v0.2.30.md and docs/APPLY-v0.2.30.md for results and limits.
Potential later work: note/effect bytecode, duration/transposition and deeper
song-specific code generation, only with complete state/timing equivalence.

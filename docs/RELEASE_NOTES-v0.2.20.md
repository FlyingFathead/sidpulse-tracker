# v0.2.20 candidate — validation repairs

This is a maintenance source candidate over v0.2.19, not a new compression backend.

The four strict py65 comparison failures came from the pinned py65 1.2.0 CPU's
`DEC absolute` ($CE) cycle-table entry: it assigns three cycles instead of the
six specified by MOS. The single-stream player's first idle callback executes
exactly one such instruction. That explains the 30-versus-27 comparison without
requiring a change to the exported player or production verifier.

A development-only adapter now uses an instance-local cycle table, changing only
this known entry to six. The upstream instruction implementation is unchanged;
no global monkeypatch, installed-package modification or new dependency is used.
The same reference is used in all four SID/PRG/stream/channel CPU test modules.
Unrecognized upstream metadata is rejected instead of silently overwritten.

The existing instrument-edit/native-save/SID-export integration test now checks
`kind == 'export_squeezer'`, the SID target, the prepared export and the unchanged
source copy. The remainder of the save-and-export test is retained.

Additional tests cover DEC byte wraparound, negative/zero/carry/decimal flags,
absolute-indexed page crossings, exact idle-call cycles, adapter isolation and
already-correct or unexpected upstream definitions. Strict event/cycle assertions
remain in place; the channel check additionally compares CIA control state.

No changes to player binaries, optimizer, encoding, GUI behavior, sequencer,
native format, dependency pins, samples, audio defaults or squeeze defaults.
See [validation and remaining release gates](VALIDATION-v0.2.20.md).

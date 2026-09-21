# v0.2.39: fit three voices in F2

F2 can show all three SID voices at narrow desktop sizes without shrinking the
song header or clipboard toolbar. **Fit 3 voice channels (F2)** is enabled by
default under **Settings Menu > UI Settings**, and is saved per user.

The grid chooses the largest font that fits voices 1–3 within the available
width, capped at the chosen page font. Row spacing remains stable. The separate
CTRL CH / FILTER column still expands and collapses. At the 8-pixel minimum,
extremely narrow views follow the selected voice rather than lose editable
fields. Turning fitting off restores the previous grid-size behavior. F5 keeps
its existing layout.

Grid fonts, rendered cells, buttons and hit rectangles are cached. Mouse editing
and drag selection use the fitted grid geometry. Audio, sequencing, sample
synthesis and exports retain their existing implementations. The previously
validated v0.2.38 CI repairs are included.

See [validation](VALIDATION-v0.2.39.md), [performance](PERFORMANCE-v0.2.39.md),
[editing details](PATTERN_EDITING.md#three-channel-fit) and
[update instructions](APPLY-v0.2.39.md).

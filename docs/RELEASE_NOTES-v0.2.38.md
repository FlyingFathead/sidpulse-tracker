# v0.2.38: UI scale hotfix

Entering F2 could shrink the entire interface even though the zoom setting
still showed the chosen value. The waveform-column layout tried to fit extra
complete channels by reducing the font used for the whole page, including the
header. The same rule affected F5.

The layout now keeps the requested font size when one complete channel and the
essential rows fit. F2 displays as many channels as fit and follows the selected
channel horizontally. The minimum-size fallback remains for very small windows
or large zoom settings so fields and the selected row stay accessible.

Only the renderer's fit calculation changes at runtime. Audio synthesis,
sequencing, sample fitting, all SQUEEZER versions, both DIGI methods and the
2048-sample default remain unchanged. The 512-sample setting remains a stress
case. Windows CI still needs confirmation on the actual runner.

See [validation](VALIDATION-v0.2.38.md), [performance](PERFORMANCE-v0.2.38.md)
and [update instructions](APPLY-v0.2.38.md).

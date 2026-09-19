# SIDpulse desktop icon

The square icon uses the supplied **SP** artwork: scanline lettering, a waveform
and the original logo's purple/red stripe colors. The full README logo is
unchanged. Startup loads and scales the PNG once before creating the pygame
window. It adds no per-frame drawing or audio work.

Windows also receives a stable application identity so SIDpulse can group its
windows separately from the Python interpreter. Linux windows use
`SIDpulseTracker` as their desktop identity. The window title includes the
tracker version. This does not rename the Python process or change the terminal
emulator's icon. Pinned shortcuts and some desktop shells use their own cached
icons; a macOS app bundle is not supplied by this source release.

On Linux, install the matching launcher and PNG icon from this checkout with:

```bash
python3 scripts/install_desktop.py
```

This optional command writes only the current user's application menu entry and
icon. It is not run automatically. The launcher uses this checkout's absolute
`run.sh` path and opens the console with the existing unsaved-work warning.
Rerun the installer if you move the checkout. Some desktops may need a menu
refresh or a newly pinned shortcut. Source ZIPs preserve executable `run.sh`.

The Linux dummy-driver tests check icon loading, pixels, startup order and no
reloading during rendering. Windows identity error handling is tested through
the API boundary; actual Windows taskbar, macOS Dock and Wayland compositor
appearance still require desktop testing.

References: [pygame window icon](https://www.pygame.org/docs/ref/display.html#pygame.display.set_icon),
[Windows application identity](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-setcurrentprocessexplicitappusermodelid),
[SDL application name](https://wiki.libsdl.org/SDL2/SDL_HINT_APP_NAME).

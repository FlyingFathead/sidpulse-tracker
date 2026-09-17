"""Drive the real asynchronous export UI without replacing its compiler."""
from time import monotonic, sleep


def finish_export_analysis(app, timeout=30.0):
    import pygame as pg
    deadline = monotonic() + timeout
    while app.dialog is not None and app.dialog.get('busy'):
        if monotonic() > deadline:
            raise AssertionError(f'Export analysis timed out: {app.dialog.get("phase")} / {app.dialog.get("detail")}')
        pg.event.pump()
        app.renderer.render(app)
        pg.display.flip()
        app.poll_export_analysis()
        sleep(0.002)
    if app.dialog is not None:
        assert not app.dialog.get('error'), app.dialog.get('error')

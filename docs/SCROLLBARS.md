# Overflow navigation

Visible vertical scrollbars use the same component in the export panel, pattern
editor, instrument/sample banks, instrument fields, settings, help, menus,
orders/pattern bank, file browser, preset list, and long messages/comments.
The bar is absent when everything fits.

Drag the thumb to move through the view or click the track above/below it to
page. Existing wheel and keyboard navigation remain available. Export also
supports Home/End; its action buttons and analysis indicator remain fixed.
Manual list scrolling only changes the viewport. Changing the selection with
keys or a row click resumes the view's normal centering/following behavior.
Scrolling does not edit notes, change the armed recording channel, add undo
entries, or overwrite a filename draft. Modals block underlying scrollbars;
changing pages, resizing, or losing focus cancels a drag.

`sidpulse/ui/scrollbar.py` accepts row or pixel units and owns clamping, thumb
geometry, track paging and drag handling. Renderers supply the content count,
visible count, selection token and local rectangle. State is bounded to the
current view, and drawing only creates a few rectangles/lines for visible bars.
It performs no song scan, file analysis, synthesis or background polling.
The export panel uses this same primitive with its pixel-based body.

See [measured UI and audio performance](PERFORMANCE-v0.2.30.md). New scrollable
views should reuse this component rather than adding a separate drag handler.

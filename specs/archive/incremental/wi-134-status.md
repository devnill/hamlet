# WI-134 Status — HelpOverlay widget

## File Created

`/Users/dan/code/hamlet/src/hamlet/tui/help_overlay.py`

## Pattern Comparison with LegendOverlay

The implementation follows the `LegendOverlay` pattern closely with these notes:

### Matches
- Same imports (`reactive`, `Static`, `from __future__ import annotations`)
- `__all__` export list
- `visible: reactive[bool] = reactive(False)` declaration
- `watch_visible` syncing `self.display = value`
- `BINDINGS` list with action names
- Corresponding `action_*` methods for binding-driven invocation
- `on_key` handler with `event.stop()`
- `render()` returning a Rich-markup string

### Differences from LegendOverlay
1. **`DEFAULT_CSS`** — `HelpOverlay` adds `DEFAULT_CSS = "HelpOverlay { display: none; }"` (per the spec). `LegendOverlay` omits this; it relies solely on `watch_visible` setting `self.display = False` on first render (since `reactive(False)` triggers the watcher at startup). Both approaches achieve the same hidden-by-default behavior; the CSS rule provides an additional guarantee.

2. **Conditional `escape` handling in `on_key`** — The spec called for `elif event.key == "escape" and self.visible`. `LegendOverlay` stops the escape event unconditionally (regardless of `visible`). The implementation follows the spec here (conditional), which avoids swallowing `Escape` keystrokes when the overlay is already hidden.

3. **Content** — `render()` shows keyboard controls (`arrows/hjkl`, `f`, `/`, `?`, `q`) rather than the symbol legend.

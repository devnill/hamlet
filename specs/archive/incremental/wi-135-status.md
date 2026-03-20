# WI-135 Status — Wire HelpOverlay into HamletApp

## Changes to `src/hamlet/tui/app.py`

**Lines changed:** ~14 lines added across 4 locations.

### 1. Import block (lines 76–82)
Added a `try/except` import for `HelpOverlay` with a fallback placeholder class, following the same pattern used for `LegendOverlay`. The fallback extends `Static` (imported as `_Static`) rather than `_Widget` since the placeholder needs to be a valid Textual widget.

### 2. BINDINGS (line 111)
Added after the legend binding:
```python
Binding("?", "toggle_help", "Help", show=True),
```
The `?` key binding lives in `HamletApp.BINDINGS` (not in `HelpOverlay`) because `Static.can_focus` is `False`, so the overlay cannot receive key events directly.

### 3. compose() (line 134)
Added `yield HelpOverlay()` immediately after `yield LegendOverlay()`.

### 4. action_toggle_help() (lines 224–230)
Added new action method:
```python
def action_toggle_help(self) -> None:
    try:
        overlay = self.query_one(HelpOverlay)
        overlay.display = not overlay.display
    except Exception as exc:
        logger.debug("toggle_help: %s", exc)
```

## Toggling Implementation

Toggling uses `overlay.display` directly (Textual's built-in CSS `display` property) rather than `overlay.visible` reactive. This avoids the conflict where `HelpOverlay.visible` shadows `DOMNode.visible` — a reactive defined on the widget class that would not correctly control Textual's rendering pipeline. The `HelpOverlay` widget's `DEFAULT_CSS` sets `display: none` as the initial state, so `action_toggle_help` flips between `none` and the default block display.

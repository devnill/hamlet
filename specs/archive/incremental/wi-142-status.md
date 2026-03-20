# WI-142 Status — Fix HelpOverlay visibility mechanism

**Status: COMPLETE**

## Changes Made

### `src/hamlet/tui/help_overlay.py`
- Removed `visible: reactive[bool] = reactive(False)` — no longer shadows `DOMNode.visible`
- Removed `watch_visible` method
- Removed `BINDINGS` list (`question_mark`, `escape`)
- Removed `on_key` method
- Removed `action_toggle_help` and `action_hide_help` action methods
- Removed `from textual.reactive import reactive` import (no longer needed)
- Removed `__all__` export list
- Kept `DEFAULT_CSS = "HelpOverlay { display: none; }"`
- Kept `render()` method (updated render string matches spec — removed `[dim]` markup from last line)

### `src/hamlet/tui/app.py`
- No changes needed. `action_toggle_help` already correctly uses `overlay.display = not overlay.display` (set by WI-135).

## Acceptance Criteria Verification

- [x] `visible` reactive removed from HelpOverlay
- [x] `DOMNode.visible` no longer shadowed
- [x] `DEFAULT_CSS` preserved: `"HelpOverlay { display: none; }"`
- [x] `render()` preserved
- [x] `app.py` `action_toggle_help` uses `overlay.display` (confirmed, no change needed)

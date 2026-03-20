# WI-139 Status: Fix stale legend key tests and update README

## Status: Complete

## Changes Made

### `tests/test_tui_app.py`
- Changed `pilot.press("?")` → `pilot.press("/")` in `test_action_toggle_legend_toggles_visibility` (two calls)
- Changed `"?" in binding_keys  # toggle_legend` → `"/" in binding_keys  # toggle_legend` in `test_bindings_defined`
- Did NOT change any `?` references for toggle_help (none existed in this file; the binding assertion was specifically for toggle_legend)

### `tests/test_tui_legend.py`
- Changed `"Press ? to toggle"` → `"Press / to toggle"` in `test_render_contains_help_text`
- Changed `"question_mark" in binding_keys` → `"slash" in binding_keys` in `test_bindings_defined`

### `README.md`
- Added "Usage" section documenting daemon/viewer workflow:
  - `hamlet daemon` — start backend server
  - `hamlet` or `hamlet view` — open TUI viewer (daemon must be running)
  - `hamlet init` — initialize hamlet for current project
- Updated Controls section: `/` = legend, `?` = help, cleaned up formatting
- Removed stale `?` = toggle legend reference

## Notes
- All changes align with WI-132 which moved toggle_legend from `?` to `/`
- The `?` binding for toggle_help (added by WI-135) is correct and untouched

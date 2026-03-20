# WI-132 Status — Change legend toggle key from `?` to `/`

## Files Modified

### `/Users/dan/code/hamlet/src/hamlet/tui/app.py`
- **Line 99**: Changed `Binding("?", "toggle_legend", "Legend", show=True)` to `Binding("/", "toggle_legend", "Legend", show=True)`

### `/Users/dan/code/hamlet/src/hamlet/tui/legend.py`
- **Line 13** (docstring): Changed `Toggle visibility with ``?``` to `Toggle visibility with ``/```
- **Line 17** (BINDINGS): Changed `("question_mark", "toggle_legend", "Toggle Legend")` to `("slash", "toggle_legend", "Toggle Legend")`
- **Line 32** (on_key docstring): Changed `Handle ``?`` to toggle` to `Handle ``/`` to toggle`
- **Line 33** (on_key condition): Changed `event.key == "question_mark"` to `event.key == "slash"`
- **Line 80** (render string): Changed `Press ? to toggle` to `Press / to toggle`

## Summary
All references to `?` as the legend toggle key have been updated to `/`. The `?` key is now free for the help overlay (WI-134). No legend functionality was changed.

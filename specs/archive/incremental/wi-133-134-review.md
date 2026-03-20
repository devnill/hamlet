## WI-133 Incremental Review

### Verdict: PASS

### Findings

All four hjkl bindings are present in `BINDINGS` at
`/Users/dan/code/hamlet/src/hamlet/tui/app.py:93-100` with the correct
action targets (`scroll_left`, `scroll_down`, `scroll_up`, `scroll_right`).

`/` is bound to `toggle_legend` at line 101.

`?` does not appear anywhere in `BINDINGS`. It is free.

No conflicts were found. The arrow-key duplicates of hjkl on lines 94, 96,
98, 100 are intentional fallbacks and do not conflict. `f` (line 102) and
`q` (line 92) are unrelated keys.

The worker's claim that no changes were needed is accurate.

---

## WI-134 Incremental Review

### Verdict: FAIL

### Findings

**F1 — `visible` reactive shadows the Textual framework property (critical)**

File: `/Users/dan/code/hamlet/src/hamlet/tui/help_overlay.py:23`

```python
visible: reactive[bool] = reactive(False)
```

`visible` is a `property` defined on `textual.dom.DOMNode` (confirmed in
Textual 8.1.1). It reads/writes CSS `visibility` and is used internally by
Textual for layout and rendering decisions. Declaring a class-level
`reactive` with the same name on the subclass replaces that property
descriptor entirely. Framework code that calls `widget.visible` will now
receive the raw `reactive` descriptor value rather than the CSS-computed
visibility, silently breaking Textual's internal visibility logic.

The `watch_visible` watcher correctly targets `self.display` (not
`self.styles.visibility`), which is good because `display: none` is the
right way to remove the widget from layout. But the reactive should not be
named `visible`. Rename it to something that does not collide with the
framework — e.g. `_shown: reactive[bool] = reactive(False)` — and rename
the watcher to `watch__shown`.

**F2 — `HelpOverlay` is not focusable; `on_key` and BINDINGS are unreachable (critical)**

File: `/Users/dan/code/hamlet/src/hamlet/tui/help_overlay.py:18-40`

`Static.can_focus` is `False` (confirmed). Textual only dispatches key
events to the focused widget and its ancestors. Because `HelpOverlay` is
never focused, neither `on_key` nor the BINDINGS (`question_mark`,
`escape`) will ever fire on this widget. The `?` toggle is completely
non-functional as implemented.

The `?` binding must live at the `App` level (or on a always-focused
ancestor) to be reachable. The acceptance criterion "on_key handles
question_mark (toggle)" is nominally present in the code but structurally
broken — it will never execute.

Fix: bind `?` in `HamletApp.BINDINGS` with an action that calls
`query_one(HelpOverlay).toggle()` or similar. The `escape` handler can
stay on the overlay only if `can_focus = True` is set and focus is moved to
the overlay when it opens.

**F3 — Redundant double-handling of keys: `on_key` and BINDINGS both cover the same events (significant)**

File: `/Users/dan/code/hamlet/src/hamlet/tui/help_overlay.py:18-40`

`on_key` intercepts `question_mark` and `escape` and calls `event.stop()`
before the binding dispatch can fire. The actions `action_toggle_help` and
`action_hide_help` defined on lines 46-52 are therefore dead code — they
can never be reached via the BINDINGS mechanism. Either use BINDINGS +
actions exclusively, or use `on_key` exclusively. Having both with
`event.stop()` in `on_key` makes the actions unreachable.

**F4 — `escape` closes the overlay regardless of focus state (minor)**

File: `/Users/dan/code/hamlet/src/hamlet/tui/help_overlay.py:38`

The `on_key` guard `and self.visible` correctly prevents closing when
already hidden. However, as noted in F2, since the widget is never focused,
this guard is moot in practice. If F2 is fixed by adding `can_focus = True`
and focusing the overlay on open, this guard is correct. If F2 is instead
fixed by moving the binding to the App level, the escape key must also be
re-homed with a corresponding visibility check.

### Unmet Acceptance Criteria

- [ ] "on_key handles question_mark (toggle)" — The handler exists in code
  but is unreachable because `Static` is not focusable (`can_focus = False`)
  and the widget is never given focus. The `?` key will not toggle the
  overlay at runtime.

## Summary

Cycle 008 adds 11 new hook scripts, extends the event schema, adds 11 daemon event handlers, wires adaptive viewport resize, adds plugin install detection, and bumps to v0.4.0. The implementation is functionally complete: all 15 hook types have scripts, hooks.json registers all 15, the event pipeline handles all 15 types end-to-end, and the TUI viewport responds to terminal resize. Two gaps stand out: test coverage does not follow the new hook types into the event pipeline or world state manager, and the `hamlet install` command was missing 11 of 15 hooks from its `HOOK_SCRIPTS` dict (fixed in this review cycle).

---

## Missing Requirements

### G1: `HOOK_SCRIPTS` in `install.py` did not cover 11 new hook types

- **Component**: `src/hamlet/cli/commands/install.py:20–25`
- **Status**: Fixed during review — all 15 hooks now present in `HOOK_SCRIPTS`.
- **Impact before fix**: Non-plugin users running `hamlet install` got only 4 of 15 hooks configured. The remaining 11 hooks (including SessionStart, SessionEnd, SubagentStart, SubagentStop, TeammateIdle, TaskCompleted, PostToolUseFailure, UserPromptSubmit, PreCompact, PostCompact, StopFailure) were never registered. `hamlet uninstall` also silently left those hooks uncleaned if installed by other means.

---

## Integration Gaps

### G2: No tests for any of the 11 new HookType values or handle_event branches

- **Components**:
  - `tests/test_event_processor.py` — no test uses any of the 11 new `HookType` values
  - `tests/test_world_state_manager.py` — no test exercises any new `handle_event` branch
  - `tests/test_tui_world_view.py` — no test for `on_mount` viewport resize call or `on_resize` handler
  - `src/hamlet/cli/commands/install.py` — `is_plugin_active()` has no test
- **Issue**: The 11 new `HookType` values added in WI-182 are not covered by any test. The 11 new branches in `handle_event()` added in WI-183 are not exercised. Specifically:
  - `HookType.SessionStart` branch calls `get_or_create_project` and `get_or_create_session` — not tested.
  - `HookType.SessionEnd` branch sets `AgentState.IDLE` under `self._lock` — not tested.
  - `HookType.SubagentStart` branch calls `get_or_create_agent` — not tested.
  - `HookType.TaskCompleted` branch calls `add_work_units` with a randomly chosen `StructureType` — not tested.
  - `on_mount` viewport resize call and `on_resize` Textual handler — not tested.
  - `is_plugin_active()` — not tested for either JSON format or the no-file case.
- **Impact**: Regressions in session and agent lifecycle handling, structure work accumulation, resize wiring, and plugin detection will not be caught by the test suite.

---

## Edge Cases Not Handled

### G3: `is_plugin_active` uses substring match — false positive risk

- **Component**: `src/hamlet/cli/commands/install.py:290`
- **Issue**: The function uses `"hamlet" in key.lower()` to match plugin keys. A user with any other plugin whose identifier contains "hamlet" as a substring would get a false positive, suppressing hook installation silently with no error or warning.
- **Impact**: Minor — edge case requiring an unusual plugin name coincidence. The silent suppression (returns 0 with a warning message) makes it visible, but the match heuristic is weak.
- **Recommendation**: Use a stricter match (e.g., exact key `"hamlet"` or check that `installPath` contains `/hamlet/`).

### G4: `notification_type` field silently discarded (pre-existing)

- **Component**: `src/hamlet/event_processing/event_processor.py`, `src/hamlet/event_processing/internal_event.py`
- **Issue**: `notification.py` sends `notification_type` in params; `validation.py` declares it in the schema; but `InternalEvent` has no `notification_type` field and `event_processor.py` does not extract it. The value is silently discarded on every Notification event.
- **Impact**: Minor and pre-existing (not introduced this cycle). Notification display is unaffected since the TUI does not yet differentiate notification types.
- **Recommendation**: Track as an open item. Downstream consumption of `notification_type` (e.g., visual distinction for progress vs. info notifications) would require adding the field to `InternalEvent` and extracting it in `process_event`.

---

## Infrastructure Gaps

None. The daemon, MCP server, validation layer, event processor, and TUI components are all wired end-to-end for the new hook types.

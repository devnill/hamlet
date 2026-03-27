# Change Plan — refine-21: Fix StatusBar dead code, validation schema, and Kitty test gaps

## What is changing and why

Two live bugs and two test coverage gaps from cycle 017.

### Bug 1: StatusBar never updates (WI-287)
`HamletApp._update_state()` (tui/app.py:178) is dead code — nothing calls it. This method is responsible for pushing agent_count, structure_count, village_name, viewport_pos, and current_activity to the StatusBar widget, and events to the EventLog widget. The status bar permanently shows zeros despite the daemon having data and WorldView rendering correctly (WorldView has its own refresh loop via `_update_animation_frame`).

### Bug 2: PostToolUseFailure events rejected (WI-288)
`EVENT_SCHEMA` in validation.py declares the `error` field as `["object", "null"]`, but the PostToolUseFailure hook sends `error` as a string. The daemon returns HTTP 400 for every PostToolUseFailure event.

### Cycle 017 G1: Agent symbol not tested (WI-289)
The Kitty integration test `test_render_frame_produces_terrain_symbols` only checks terrain symbols. No test asserts that agent `@` appears in render output.

### Cycle 017 G2: Empty state not tested (WI-290)
No integration test covers the Kitty pipeline with empty agents/structures/villages (fresh daemon installation).

## Scope Boundary

**Changing:**
- `src/hamlet/tui/app.py` — wire `_update_state()` into `_refresh_remote_state()`
- `src/hamlet/mcp_server/validation.py` — accept string type for error field
- `tests/test_kitty_integration.py` — add agent symbol and empty-state tests
- `tests/fixtures/daemon_state_empty.json` — new empty-state fixture

**Not changing:** Daemon, hooks, Kitty viewer, Textual WorldView, terrain, persistence, simulation, CLI, architecture.

## Work Items

| ID | Title |
|----|-------|
| WI-287 | Wire _update_state into refresh loop |
| WI-288 | Fix validation schema error field type |
| WI-289 | Add agent symbol assertion to Kitty integration test |
| WI-290 | Add empty-state Kitty integration test |

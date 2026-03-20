# WI-127 Status: Create viewer mode and refactor entry point

## Files Created

- `src/hamlet/tui/remote_state.py` — `RemoteStateProvider` class with `start()`, `stop()`, `check_health()`, `fetch_state()`, `fetch_events()`
- `src/hamlet/tui/remote_world_state.py` — `RemoteWorldState` class plus deserialization helpers

## Files Modified

- `src/hamlet/__main__.py` — added `_run_viewer(base_url)` async function (existing `_run_app()` preserved unchanged)
- `src/hamlet/tui/app.py` — added `remote_provider: RemoteStateProvider | None = None` param to `HamletApp.__init__`; added `_refresh_remote_state()` and conditional `set_interval` in `on_mount`

## Methods Implemented in RemoteWorldState

| Method | Notes |
|---|---|
| `refresh()` | Fetches `/hamlet/state` and `/hamlet/events`, updates all caches |
| `get_all_agents()` | Returns cached `list[Agent]` |
| `get_all_structures()` | Returns cached `list[Structure]` |
| `get_all_villages()` | Returns cached `list[Village]` |
| `get_projects()` | Returns cached `list[Project]` |
| `get_event_log(limit)` | Returns last `limit` entries from cached event log |
| `get_agents_in_view(bounds)` | Filters cached agents by bounding box |
| `get_structures_in_view(bounds)` | Filters cached structures by bounding box |
| `get_animation_frame()` | Returns 0 (not tracked remotely) |

## Deviations from Spec

- `ActivityType` enum referenced in the spec does not exist anywhere in the codebase; it was omitted from deserialization (no fields use it).
- `_run_viewer` performs an initial `refresh()` call before `viewport.initialize()` so the viewport can centre on a village if one is present in the remote state.
- The background refresh interval in `HamletApp` calls `self._world_state.refresh()` (a `RemoteWorldState` method) — the call is guarded by `type: ignore[attr-defined]` since `WorldStateManager` does not expose `refresh()`, preserving full backward compatibility.

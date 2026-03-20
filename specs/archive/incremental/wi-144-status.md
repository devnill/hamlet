# WI-144 Status — Fix RemoteWorldState correctness issues

**Status: COMPLETE**

## Changes Made

### `src/hamlet/tui/remote_world_state.py`

1. **`get_animation_frame`** — Changed from `async def get_animation_frame(self) -> int` to `def get_animation_frame(self, agent_id: str) -> int`. Returns `self._cached_state.get("animation_frames", {}).get(agent_id, 0)`.
   - Added `self._cached_state: dict = {}` to `__init__` to back this method.
   - `refresh()` now stores the raw state dict in `self._cached_state = state` before parsing.

2. **`get_event_log`** — Changed `[-limit:]` to `[:limit]` so the method returns the first `limit` entries (matching the expected ordering from the daemon, which already returns newest-first or in insertion order).

3. **`_parse_agent`** — Changed `d["id"]` to `d.get("id", "")` to eliminate KeyError risk.

4. **`_parse_structure`** — Changed `d["id"]` to `d.get("id", "")` (same fix, same risk).

5. **`_parse_village`** — Changed `d["id"]` to `d.get("id", "")` (same fix for consistency).

6. **`_parse_project`** — Changed `d["id"]` to `d.get("id", "")` (same fix for consistency).

### `src/hamlet/tui/remote_state.py`

Added `if self._session is None:` guards before all HTTP calls in:
- `check_health` — returns `False` if session is None
- `fetch_state` — returns `{}` if session is None
- `fetch_events` — returns `[]` if session is None

Removed the `# type: ignore[union-attr]` comments that were suppressing the None-access type errors (now unnecessary since the guards handle the None case explicitly).

### `src/hamlet/tui/app.py`

Fixed `_refresh_remote_state` to use `hasattr` guard instead of `# type: ignore[attr-defined]`:
```python
async def _refresh_remote_state(self) -> None:
    try:
        if hasattr(self._world_state, "refresh"):
            await self._world_state.refresh()
    except Exception as exc:
        logger.debug("_refresh_remote_state: failed: %s", exc)
```

## Acceptance Criteria Verified

- [x] `get_animation_frame(self, agent_id: str) -> int` — synchronous, takes agent_id
- [x] `get_event_log` uses `[:limit]` not `[-limit:]`
- [x] `_parse_agent` uses `d.get("id", "")`
- [x] `RemoteStateProvider` methods guard against `None` session

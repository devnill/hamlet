## Verdict: Fail

Two critical findings fixed: stale viewport state due to wrong capture ordering, and unencapsulated access to private `_state` dicts without the manager lock.

## Critical Findings

### C1: `viewport_state` captured before `_viewport.update()` — stale position in status bar
- **File**: `src/hamlet/tui/app.py:130`
- **Issue**: `viewport_state` and `bounds` were captured before `await self._viewport.update()`. In follow mode, `update()` moves the viewport center; the captured state was one tick stale.
- **Impact**: Status bar always showed the previous tick's viewport position. Bounds passed to agent/structure queries were also stale.
- **Fix applied**: Moved `await self._viewport.update()` to run first; `viewport_state` and `bounds` now captured from the updated viewport.

### C2: Direct access to `_world_state._state.projects` and `_state.agents` bypasses public API
- **File**: `src/hamlet/tui/app.py:145,199`
- **Issue**: `self._world_state._state.projects` and `self._world_state._state.agents` accessed directly, bypassing `WorldStateManager` encapsulation and the internal `_lock`.
- **Impact**: Breaks encapsulation; accessing private state without the manager lock is unsafe if other coroutines are mutating it.
- **Fix applied**: Added `get_projects()` and `get_all_agents()` public methods to `WorldStateManager`; updated `_update_state` and `action_toggle_follow` to use them. `action_toggle_follow` made `async` to allow `await`.

## Significant Findings

None.

## Minor Findings

None.

## Unmet Acceptance Criteria

None — all criteria satisfied after rework.

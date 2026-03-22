## Verdict: Fail

The four Cycle 6 work items are individually correct, but WI-216 introduces an unbounded expansion loop: `process_expansion` has no per-village cooldown, so any village at or above `expansion_threshold` agents will attempt to found a new outpost and rebuild its road on every simulation tick (~30 times per second).

## Critical Findings

None.

## Significant Findings

### S1: `process_expansion` founds outposts and rebuilds roads on every tick with no cooldown

- **File**: `/Users/dan/code/hamlet/src/hamlet/simulation/expansion.py:66`
- **Issue**: `process_expansion` runs for every village every tick. The only gate is `check_village_expansion`, which returns a site whenever `len(agents) >= expansion_threshold`. Once a village reaches 20 agents the condition stays true permanently, so on every subsequent tick the engine calls `create_road_between` (which calls `create_structure` once per road cell, each acquiring `WorldStateManager._lock`) and then calls `found_village`. The `found_village` 5-cell idempotency guard prevents duplicate village records, but `create_road_between` has no deduplication. `_create_structure_locked` does not check whether a structure already exists at a position before inserting — it calls `self._grid.occupy()`, catches the `ValueError` on collision, logs a warning, and then proceeds to add the structure to `self._state.structures` and call `self._persistence.queue_write` anyway. Road cells are therefore re-inserted into the structures dict and re-queued for persistence on every tick that the village is large enough. At the default 30 ticks/s, a road of N cells generates N new phantom structure records per second in both memory and SQLite.
- **Impact**: Unbounded memory growth in `self._state.structures`, unbounded SQLite write queue pressure, and lock contention from O(road_length) lock acquisitions per tick. Road cells accumulate as duplicate entries in the render data, breaking the visual display.
- **Suggested fix**: Track per-village expansion state. Add a `has_expanded: bool = False` flag (dataclass field) to `Village`, set it to `True` inside `WorldStateManager.found_village` on the originating village, and check it at the top of the per-village loop in `process_expansion` — skipping any village for which `village.has_expanded` is True. This caps each village at one expansion event for its lifetime.

## Minor Findings

### M1: `zombie_despawn_seconds` has no validation in `Settings._validate()`

- **File**: `/Users/dan/code/hamlet/src/hamlet/config/settings.py:21`
- **Issue**: WI-214 added `zombie_threshold_seconds` with full type, bool, and positive-integer validation. The companion field `zombie_despawn_seconds` (present before Cycle 6) has no validation at all. A config file containing `"zombie_despawn_seconds": 0` or `"zombie_despawn_seconds": "300"` produces no startup error; the bad value is passed directly to `AgentInferenceEngine` where it will cause incorrect behavior or a downstream `TypeError`.
- **Suggested fix**: Add matching validation after the `zombie_threshold_seconds` block.

### M2: `Optional` imported but never used in `settings.py`

- **File**: `/Users/dan/code/hamlet/src/hamlet/config/settings.py:6`
- **Issue**: `from typing import Optional` is present but `Optional` is not referenced anywhere in the module.
- **Suggested fix**: Remove the import line.

### M3: `fetch_state` and `fetch_events` do not catch network exceptions at the method level

- **File**: `/Users/dan/code/hamlet/src/hamlet/tui/remote_state.py:37-56`
- **Issue**: `check_health` wraps its request in `try/except Exception` and returns a safe default on failure. `fetch_state` and `fetch_events` propagate all aiohttp exceptions to the caller. The current call site catches them, but the asymmetry means any future caller must remember to add its own try/except.
- **Suggested fix**: Add `try/except Exception` in `fetch_state` returning `{}` and in `fetch_events` returning `[]`, matching `check_health`.

## Unmet Acceptance Criteria

None.

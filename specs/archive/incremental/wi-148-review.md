## Verdict: Fail

The `_parse_dt` helper is correctly placed on all required fields, but it produces naive `datetime` objects when the database stores naive ISO strings (the SQLite default), while `AgentUpdater` computes `datetime.now(UTC)` (timezone-aware); subtracting the two raises `TypeError`, so zombie and idle detection remain broken after reload.

## Critical Findings

### C1: _parse_dt produces naive datetimes; AgentUpdater uses timezone-aware now — subtraction raises TypeError

- **File**: `src/hamlet/persistence/loader.py:30`
- **Issue**: When `value` is an ISO string without a timezone suffix (the default for SQLite-stored timestamps), `datetime.fromisoformat(str(value))` returns a naive `datetime`. `AgentUpdater.update_agents` computes `now = datetime.now(UTC)` (timezone-aware) and then does `now - agent.last_seen`. Python raises `TypeError: can't subtract offset-naive and offset-aware datetimes` at that point, crashing the update loop for every agent loaded from persistence.
- **Impact**: Zombie and idle detection fail completely for all agents that were reloaded from the database, which is the central acceptance criterion of the work item.
- **Suggested fix**: Force UTC-awareness in `_parse_dt` for the string branch:
  ```python
  dt = datetime.fromisoformat(str(value))
  if dt.tzinfo is None:
      dt = dt.replace(tzinfo=timezone.utc)
  return dt
  ```
  This is safe because SQLite always stores UTC strings when written by the existing saver.

### C2: WorldStateManager.load_from_persistence re-parses last_seen after loader already converted it — incorrect isinstance guard treats a datetime as a string

- **File**: `src/hamlet/world_state/manager.py:100`
- **Issue**: Line 100 reads:
  ```python
  last_seen=datetime.fromisoformat(d["last_seen"]) if isinstance(d.get("last_seen"), str) else (d.get("last_seen") or datetime.now(UTC)),
  ```
  After WI-148, `d["last_seen"]` is already a `datetime` object (not a string), so the `isinstance(..., str)` branch is never taken and the else branch silently returns the `datetime` as-is. If `_parse_dt` returns a naive datetime (per C1), this line passes it through unchanged. The `datetime.fromisoformat` call here is now dead code, but the real problem is that this consumer was clearly written assuming the loader returns strings — confirming that the loader's output contract was not communicated or enforced, and that if `_parse_dt` is ever removed the manager silently regresses with no type error to indicate the problem.
- **Impact**: Dead code masking the integration contract; the None-fallback `or datetime.now(UTC)` is also timezone-aware, so if _parse_dt is fixed (C1), the mismatched-timezone bug resurfaces here for the fallback path.
- **Suggested fix**: Remove the inline re-parsing and rely solely on what the loader provides. If the loader's output contract is `datetime`, assert it:
  ```python
  last_seen=d["last_seen"],  # loader guarantees datetime via _parse_dt
  ```
  and add a type assertion in tests. The guard in manager.py should not exist if the loader is trusted.

## Significant Findings

### S1: No test asserts that loaded datetime fields are datetime instances

- **File**: `tests/test_persistence_loader.py:91`
- **Issue**: The integration test for `_load_agents` (line 91) asserts `agent["id"]`, `agent["inferred_type"]`, and `agent["position_x"]`, but never checks `isinstance(agent["last_seen"], datetime)`, `isinstance(agent["created_at"], datetime)`, or `isinstance(agent["updated_at"], datetime)`. The same omission applies to the project and structure assertions. The core acceptance criterion — that load methods return `datetime` objects not ISO strings — is not verified by any test.
- **Impact**: A regression that re-introduces string timestamps would pass the entire test suite undetected.
- **Suggested fix**: Add assertions in `test_load_state_returns_world_state_data`:
  ```python
  assert isinstance(agent["last_seen"], datetime)
  assert isinstance(agent["created_at"], datetime)
  assert isinstance(agent["updated_at"], datetime)
  assert isinstance(project["created_at"], datetime)
  assert isinstance(structure["created_at"], datetime)
  ```

### S2: _load_sessions and _load_villages do not apply _parse_dt to their timestamp columns

- **File**: `src/hamlet/persistence/loader.py:91` (`_load_sessions`), `src/hamlet/persistence/loader.py:118` (`_load_villages`)
- **Issue**: `_load_sessions` fetches `started_at` and `last_activity` but returns them as raw DB values (ISO strings or whatever SQLite returns). `_load_villages` fetches `created_at` and `updated_at` but returns them raw via the one-liner list comprehension on line 136. The work item scope names only `_load_agents`, `_load_structures`, and `_load_projects`, but the fix is inconsistently applied across the codebase — any consumer of session or village timestamps will encounter the same string/datetime mismatch.
- **Impact**: If any code computes time deltas from session or village timestamps after a reload, it will raise `TypeError` or silently compare incompatible types.
- **Suggested fix**: Apply `_parse_dt` to `started_at` and `last_activity` in `_load_sessions`, and to `created_at` and `updated_at` in `_load_villages`, using the same pattern established for the other three loaders.

## Minor Findings

### M1: _parse_dt None-fallback silently substitutes current time, masking data integrity issues

- **File**: `src/hamlet/persistence/loader.py:27`
- **Issue**: When `value` is `None`, `_parse_dt` returns `datetime.now(timezone.utc)` rather than raising or logging. A NULL timestamp in the DB is a data integrity problem; substituting the current time means every zombie/idle calculation for an agent with a NULL `last_seen` will silently treat that agent as having been seen "just now," keeping it perpetually ACTIVE.
- **Suggested fix**: Log a warning before returning the fallback:
  ```python
  log.warning("_parse_dt: NULL timestamp encountered; substituting current UTC time")
  return datetime.now(timezone.utc)
  ```
  This preserves graceful degradation (GP-7) while making the anomaly visible in logs.

## Unmet Acceptance Criteria

- [ ] **datetime.fromisoformat() used to parse timestamp columns from DB** — `_parse_dt` does call `fromisoformat`, but it produces naive datetimes for naive ISO strings (the SQLite default). The resulting objects are not safely usable with timezone-aware arithmetic, so the parsing is functionally incomplete.
- [ ] **Zombie and idle detection work correctly after reload from persistence** — Broken by C1: `AgentUpdater` subtracts a naive `datetime` from a timezone-aware `datetime.now(UTC)`, raising `TypeError` at runtime for every reloaded agent.

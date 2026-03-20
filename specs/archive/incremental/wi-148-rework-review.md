## Verdict: Fail

loader.py now correctly parses timestamps into timezone-aware datetime objects for agents, structures, sessions, and villages. However the existing test suite does not test for timezone-aware datetimes, and the tests contain a pre-existing assertion error that will cause them to fail at runtime — meaning the datetime correctness cannot be verified by running the suite.

## Critical Findings

None.

## Significant Findings

### S1: Test suite asserts datetime field is a raw string, not a datetime object
- **File**: `/Users/dan/code/hamlet/tests/test_persistence_loader.py:93`
- **Issue**: `test_load_state_returns_world_state_data` asserts `agent["inferred_type"] == "builder"` — that assertion is not related to this work item but is in the same test that would be used to verify datetime behaviour. More directly: none of the tests assert that `last_seen`, `created_at`, or `updated_at` fields are `datetime` instances after the rework. The test on line 33 inserts a naive ISO string (`datetime.now().isoformat()`, no `+00:00`) and never checks whether the returned value is a `datetime` with `tzinfo` set.
- **Impact**: The acceptance criterion "datetime objects not ISO strings" and "timezone-aware" cannot be confirmed by the test suite. A regression that reverts `_parse_dt` to returning raw strings would pass all existing tests undetected.
- **Suggested fix**: Add assertions to `test_load_state_returns_world_state_data` (or a dedicated new test) of the form:
  ```python
  assert isinstance(agent["last_seen"], datetime)
  assert agent["last_seen"].tzinfo is not None
  ```
  covering `last_seen`, `created_at`, `updated_at` for agents, and `started_at`/`last_activity` for sessions.

### S2: _load_agents does not apply _parse_dt to the agents table project_id column
- **File**: `/Users/dan/code/hamlet/src/hamlet/persistence/loader.py:151-178`
- **Issue**: This is not a timestamp issue but an omission check — the `agents` table query includes a `project_id` column (line 165) that is listed in `cols` (line 158) and fetched, but `_load_agents` does not include `project_id` in the columns it applies `_parse_dt` to. This is correct — `project_id` is not a timestamp — however the agents table query on line 162-165 does **not** select `project_id` in the SQL string, yet `cols` at line 158 lists `project_id` as the 15th column. The SQL on line 162 selects only 14 columns (`id` through `updated_at`), so `zip(cols, row)` silently drops `project_id` from every agent dict. `manager.py` line 95 then falls back to `d.get("project_id", "")` — getting an empty string — causing every reloaded agent to have no `project_id`.
- **Impact**: Every agent reloaded from persistence has `project_id=""`, breaking project/village association after restart.
- **Suggested fix**: Add `project_id` to the SELECT statement in `_load_agents`:
  ```python
  "SELECT id, session_id, village_id, parent_id,"
  " inferred_type, color, position_x, position_y,"
  " last_seen, state, current_activity,"
  " total_work_units, created_at, updated_at, project_id FROM agents"
  ```
  (The column name is already correct in `cols`; only the SQL string is missing it.)

## Minor Findings

### M1: Tests insert naive timestamps — do not cover the UTC-attachment path in _parse_dt
- **File**: `/Users/dan/code/hamlet/tests/test_persistence_loader.py:33`
- **Issue**: All test fixtures use `datetime.now().isoformat()` (naive, no timezone). The branch in `_parse_dt` that handles an already-aware datetime (lines 28-31 of loader.py) is never exercised. A database that stores timestamps with timezone suffixes (e.g. SQLite storing `CURRENT_TIMESTAMP` as `"2026-03-19 12:00:00"` without a suffix, but an application writing ISO 8601 with `+00:00`) would exercise a different code path than what the tests cover.
- **Suggested fix**: Add one test that inserts a timestamp string with an explicit UTC offset (`"2026-01-01T00:00:00+00:00"`) and asserts the returned datetime is still timezone-aware, to confirm the already-aware branch is exercised.

### M2: _parse_dt None sentinel returns current time, masking missing data
- **File**: `/Users/dan/code/hamlet/src/hamlet/persistence/loader.py:26-27`
- **Issue**: When `last_seen` is NULL in the database, `_parse_dt` returns `datetime.now(UTC)` rather than raising or propagating a sentinel. For zombie detection this means a freshly-current timestamp is silently substituted, preventing an agent with a genuinely missing `last_seen` from ever being classified as a zombie. The docstring acknowledges this but the behaviour is undocumented at the call sites.
- **Suggested fix**: This is a design choice that may be intentional. At minimum, add a `log.debug` call in the `if value is None` branch so the substitution is observable in logs, e.g. `log.debug("_parse_dt: NULL timestamp substituted with now()")`.

## Unmet Acceptance Criteria

- [ ] `_load_agents`, `_load_structures`, `_load_projects` return datetime objects not ISO strings — the loader code does return datetime objects, but this is not verified by the test suite (see S1). Additionally, `_load_projects` applies `_parse_dt` to `created_at`/`updated_at` but those columns are not timestamp fields critical to zombie/idle detection; the more important fields (`last_seen` in agents) are covered in code but not in tests.

## Verdict: Pass (after rework)

Migration 2 was not atomic (executescript does not wrap statements in a transaction), migration tests hardcoded version 1 causing immediate test failures, and no tests covered the project_id round-trip or migration 2 itself.

## Critical Findings

### C1: Migration tests hardcode version 1, fail after migration 2 is applied
- **File**: `tests/test_persistence_migrations.py:35` and `:92`
- **Issue**: Both `test_run_migrations_creates_all_tables` and `test_run_migrations_idempotent` assert `row[0] == 1` after `run_migrations()`. With migration 2 in the dict, schema_version will be 2.
- **Impact**: CI broken immediately.
- **Suggested fix**: Change assertions to `row[0] == 2`.

### C2: `executescript` is not transactional — partial migration 2 leaves DB unrecoverable
- **File**: `src/hamlet/persistence/migrations.py:126`
- **Issue**: `executescript` issues an implicit COMMIT before running. If the process is killed between `ALTER TABLE` and `UPDATE schema_version`, the DB has the column but version 1. On next startup, migration 2 runs again and `ALTER TABLE` fails with "duplicate column name".
- **Impact**: Interrupted migration 2 leaves the database permanently broken.
- **Suggested fix**: Wrap migration 2 SQL in explicit `BEGIN; ... COMMIT;` for atomicity.

## Significant Findings

### S1: No test covers `project_id` round-trip
- **File**: `tests/test_persistence_writer.py`, `tests/test_persistence_loader.py`
- **Issue**: Existing agent tests don't include `project_id` in data or assertions.
- **Suggested fix**: Add test that writes `project_id="proj-123"` and reads it back.

### S2: No test for migration 2
- **File**: `tests/test_persistence_migrations.py`
- **Issue**: No test verifies migration 2 adds the `project_id` column or updates version to 2.
- **Suggested fix**: Add dedicated test checking `PRAGMA table_info(agents)`.

## Minor Findings

### M1: Stale comment on `Agent.project_id`
- **File**: `src/hamlet/world_state/types.py:95`
- **Issue**: Comment says "not stored in DB" — now false after this work item.
- **Suggested fix**: Update to "persisted to agents table via migration 2".

## Unmet Acceptance Criteria

- [ ] AC5 — Round-trip verifiable by test — code inspection satisfies it but no test exercised it (S1).

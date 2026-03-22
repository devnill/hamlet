# Review: WI-217 — Add Village.has_expanded flag and per-village expansion cooldown

## Verdict: Pass

All critical and significant findings from the previous review have been resolved. The implementation is correct.

---

## Rework Applied (from Verdict: Fail pass)

**C1 resolved**: `has_expanded = True` is now set on the originating village even when the 5-cell idempotency guard fires (early return path). The fix adds the `has_expanded` assignment inside the guard's early-return branch before `return existing`, so both the new-village path and the guard-fires path mark the originating village as expanded.

**S1 resolved**: Two new tests added to `test_world_state_manager.py`:
- `test_found_village_sets_has_expanded_on_originating_village` — verifies `has_expanded = True` is set when a new village is created
- `test_found_village_sets_has_expanded_even_when_guard_fires` — verifies `has_expanded = True` is set when the proximity guard returns an existing village

**S2 resolved**: All four `@pytest.mark.asyncio` decorators removed from `test_persistence_migrations.py` (lines 19, 76, 122, 131), in compliance with project `CLAUDE.md` convention.

---

## Remaining Minor Findings

### M1: Migration dict literal in descending order (cosmetic)

- **File**: `src/hamlet/persistence/migrations.py`
- Migration 3 appears before migration 2 in the dict literal. Execution order is correct (`sorted()` is used). Cosmetic only; no functional impact.

### M2: No `test_migration_3_adds_has_expanded_column` test

- **File**: `tests/test_persistence_migrations.py`
- No test uses `PRAGMA table_info(villages)` to verify `has_expanded` was added by migration 3. The schema-version assertions confirm migration 3 ran, but column existence is not directly asserted.

These minor findings do not block acceptance.

---

## Acceptance Criteria

- [x] **AC1**: `Village` dataclass has `has_expanded: bool = False` — met
- [x] **AC2**: `WorldStateManager.found_village` sets `has_expanded = True` on the originating village — met (both new-village path and guard-fires path)
- [x] **AC3**: `process_expansion` skips villages where `has_expanded is True` — met
- [x] **AC4**: Test verifies `has_expanded = True` prevents further expansion — met
- [x] **AC5**: `has_expanded` persisted in SQLite (migration, loader, writer) — met

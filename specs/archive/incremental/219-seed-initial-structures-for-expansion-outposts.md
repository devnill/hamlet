# Review: WI-219 — Seed initial structures for expansion outposts

## Verdict: Pass

The implementation is correct. `_seed_initial_structures` is called outside the lock block in `found_village`, following the same pattern as `get_or_create_project`. The required test verifies at least one structure is seeded.

---

## Findings

### No critical or significant findings.

### M1: Test only asserts `>= 1` structure, not specific structure types

- **File**: `tests/test_world_state_manager.py:873`
- `test_found_village_seeds_initial_structures` asserts `len(structures_for_village) >= 1`. `_seed_initial_structures` places LIBRARY, WORKSHOP, and FORGE — the test could assert exactly 3 structures of those types, which would catch regressions in seeding logic more precisely.
- **Impact**: Minimal. Any call to `create_structure` in `_seed_initial_structures` satisfies the assertion. A future change that seeds only 1 structure would still pass.
- **Suggested fix**: Not required for acceptance; leave as is unless stricter coverage is desired.

### M2: `village_to_seed` sentinel pattern adds complexity

- **File**: `src/hamlet/world_state/manager.py`
- The `village_to_seed: Village | None = None` sentinel is needed because the early-return idempotency path must not seed structures for an already-existing village. The pattern is correct and matches the WI-219 notes' stated constraint. Noted for future readers: this is intentional, not accidental complexity.

---

## Acceptance Criteria

- [x] **AC1**: `found_village` calls `_seed_initial_structures(new_village)` after the lock block — met
- [x] **AC2**: Call is outside `async with self._lock:` (deadlock prevention) — met; `village_to_seed` sentinel ensures the call only happens on the new-village path, outside the lock
- [x] **AC3**: Test in `test_world_state_manager.py` asserts at least one structure returned after `found_village` — met (`test_found_village_seeds_initial_structures`)
- [x] **AC4**: Idempotency guard path does not seed structures for existing village — met; `village_to_seed` remains `None` on early return, so `_seed_initial_structures` is not called

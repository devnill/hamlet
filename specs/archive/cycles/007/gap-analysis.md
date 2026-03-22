## Summary

Cycle 7 addressed three significant gaps from the prior review: unbounded expansion re-triggering (WI-217), incomplete WorldStateProtocol (WI-218), and empty expansion outposts (WI-219). During the comprehensive review, two additional critical gaps were found and fixed within the cycle: `has_expanded` was missing from the API serializer (`_serialize_village`) and the TUI deserializer (`_parse_village`). No critical or significant gaps remain.

## Critical Gaps

None.

## Significant Gaps

None.

## Minor Gaps

### MG1: Migration 3 column existence not directly tested

- **File**: `tests/test_persistence_migrations.py`
- `test_migration_2_adds_project_id_column` verifies column existence via `PRAGMA table_info`. No equivalent test for migration 3's `has_expanded` column on the `villages` table. Schema-version assertions confirm migration 3 ran but don't verify the column was added.
- **Impact**: A typo in the migration SQL that adds the wrong column name would go undetected.

### MG2: `test_found_village_seeds_initial_structures` uses a weak structure-count assertion

- **File**: `tests/test_world_state_manager.py`
- Asserts `len(structures_for_village) >= 1` but `_seed_initial_structures` should place exactly 3 structures (LIBRARY, WORKSHOP, FORGE). A regression that drops two of the three seeded structures would pass the test.
- **Impact**: Reduced confidence in structure-seeding correctness for outposts.

### MG3: `Village.has_expanded` round-trip through serializer not tested

- **Context**: The serializer now correctly includes `has_expanded` and `_parse_village` deserializes it, but no test explicitly round-trips a village with `has_expanded=True` through serialize→deserialize and asserts the field is preserved.
- **Impact**: Low — the field assignment is trivial, but regression coverage is absent.

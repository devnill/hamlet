## Verdict: Fail

The implementation is largely correct but the idempotency test for AC4 does not exercise the inner 5-cell guard in `found_village`, and the new tests use `@pytest.mark.asyncio` decorators that are explicitly prohibited by the project's testing conventions.

## Critical Findings

None.

## Significant Findings

### S1: AC4 idempotency guard is not tested at the `found_village` level

- **File**: `/Users/dan/code/hamlet/tests/test_expansion.py:282-341`
- **Issue**: `test_process_expansion_no_duplicate_village` only validates that a second tick does not re-select the same expansion site because `_is_clear_site` rejects it (15-cell guard in `check_village_expansion`). The test comment on lines 295-298 acknowledges the 5-cell inner guard in `found_village` also protects against duplicates, but there is no test that drives a call to `found_village` with a site within 5 cells of an existing village and asserts the existing village is returned. If the 15-cell guard were removed or loosened, the inner guard would silently fail without any test catching it.
- **Impact**: AC4 states "a second expansion check does not create a duplicate settlement at the same site." The inner guard is tested only indirectly; a regression in the 5-cell threshold or the guard logic would not be caught.
- **Suggested fix**: Add a direct unit test for `found_village` that calls it twice with the same (or nearby) center and asserts `call_count` on `queue_write` is 1 and the returned village on the second call is the same object.

## Minor Findings

### M1: `@pytest.mark.asyncio` decorators on async test methods

- **File**: `/Users/dan/code/hamlet/tests/test_expansion.py:136` and `:224`
- **Issue**: `CLAUDE.md` explicitly states "`asyncio_mode = "auto"` is set in `pyproject.toml` — do not add `@pytest.mark.asyncio` decorators; they are unnecessary and may cause warnings." Lines 136 and 224 add these decorators to the two new tests for this work item.
- **Suggested fix**: Remove both `@pytest.mark.asyncio` decorators. The `asyncio_mode = "auto"` configuration handles async test discovery automatically.

### M2: `hasattr` duck-type guard is fragile

- **File**: `/Users/dan/code/hamlet/src/hamlet/simulation/expansion.py:83`
- **Issue**: `if hasattr(world_state, "found_village"):` silently skips village creation if the method is missing on a real `WorldStateManager`. This guard was presumably added for backward compatibility with mock objects in tests that do not set up `found_village`, but it means a misconfigured production world_state will silently produce expansions without new villages, with no log warning.
- **Suggested fix**: Remove the `hasattr` guard and ensure all tests that call `process_expansion` supply a `world_state` mock with `found_village` set (or use `spec=WorldStateManager` on the mock). If backward compatibility is genuinely needed, at minimum add a `logger.warning` when the attribute is absent.

## Unmet Acceptance Criteria

- [ ] AC4: "A second expansion check does not create a duplicate settlement at the same site (idempotency)" — The 5-cell proximity guard in `found_village` is untested at the unit level. The test only exercises the outer `_is_clear_site` (15-cell) path, leaving the inner guard unverified by any assertion.

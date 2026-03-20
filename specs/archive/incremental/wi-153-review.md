## Verdict: Fail

The implementation formula is correct but all four unit tests for work unit accumulation assert expected values from the old formula, meaning the tests will fail against the new code.

## Critical Findings

### C1: Work unit tests assert old formula values — all four will fail
- **File**: `/Users/dan/code/hamlet/tests/test_type_inference.py:515`, `:530`, `:545`, `:571`
- **Issue**: The engine was changed to `int(duration_ms * work_unit_scale)` with a `0` default when `duration_ms is None`. With the default `work_unit_scale=1.0`, the expected values are:
  - `duration_ms=None` → `0` (not `1`; line 515 asserts `1`)
  - `duration_ms=500` → `500` (not `5`; line 530 asserts `5`)
  - `duration_ms=99` → `99` (not `1`; line 545 asserts `1`)
  - `duration_ms=200` → `200` (not `2`; line 571 asserts `2`)

  The test docstrings still describe `max(1, duration_ms // 100)`, which is the old formula. None of the tests pass a custom `SimulationConfig` to the engine, so `work_unit_scale=1.0` is in effect for all of them.
- **Impact**: Running the test suite will produce four assertion failures. The CI gate will break and the worker self-check claim that the formula is satisfied is wrong.
- **Suggested fix**: Either update the four tests to use the new formula's expected values and add a test that passes a non-1.0 `work_unit_scale` to verify the config is respected, **or** restore a minimum-1 clamp in the engine if the old behaviour was intentional. For the new formula the corrected assertions are:
  ```python
  # duration_ms=None  → 0
  ws.add_work_units.assert_awaited_once_with(agent_id, StructureType.FORGE, 0)

  # duration_ms=500, scale=1.0  → 500
  ws.add_work_units.assert_awaited_once_with(agent_id, StructureType.FORGE, 500)

  # duration_ms=99, scale=1.0  → 99
  ws.add_work_units.assert_awaited_once_with(agent_id, StructureType.FORGE, 99)

  # duration_ms=200, scale=1.0  → 200
  ws.add_work_units.assert_awaited_once_with(agent_id, StructureType.LIBRARY, 200)
  ```

## Significant Findings

### S1: `duration_ms=None` yields 0 work units — no minimum applied
- **File**: `/Users/dan/code/hamlet/src/hamlet/inference/engine.py:277`
- **Issue**: When `event.duration_ms is None`, `units` is set to `0` and `add_work_units` is called with `0`. This means a tool completion with no reported duration contributes nothing to structure progression and silently drops the call's contribution. There is no documented decision to treat missing duration as zero work.
- **Impact**: Any tool event that arrives without a `duration_ms` (e.g. from a hook implementation that omits the field) will silently produce no world-building effect. This is a behaviour regression from the old formula which gave a minimum of 1.
- **Suggested fix**: Apply a minimum of 1 when `duration_ms is None`, or skip the call entirely and log at DEBUG level so the omission is visible:
  ```python
  if event.duration_ms is None:
      units = 1  # minimum one unit for any completed tool call
  else:
      units = max(1, int(event.duration_ms * self._config.work_unit_scale))
  ```

## Minor Findings

### M1: Test docstrings describe the old formula after refactor
- **File**: `/Users/dan/code/hamlet/tests/test_type_inference.py:520`, `:534`
- **Issue**: `test_work_units_formula_500ms` documents `max(1, 500//100) = 5` and `test_work_units_formula_clamped_to_1_for_small_duration` documents `max(1, 99//100) = max(1, 0) = 1`. These docstrings describe the removed formula and will mislead future readers.
- **Suggested fix**: Update docstrings to state the new formula, e.g. `500 * 1.0 = 500` and `99 * 1.0 = 99`.

## Unmet Acceptance Criteria

- [ ] **Work unit formula: duration_ms * SimulationConfig.work_unit_scale** — The formula in the engine (`int(event.duration_ms * self._config.work_unit_scale)`) is correct, but the tests were not updated to match it. The worker self-check marks this satisfied, but the tests still encode the old `max(1, duration_ms // 100)` formula and will fail, demonstrating the criterion is not verified by the test suite.

# Code Quality Report — Cycle 010

**Scope**: WI-199 (end_turn stop_reason guard), WI-200 (notification_type differentiation)
**Date**: 2026-03-20
**Reviewer**: Claude Sonnet 4.6

---

## Verdict: Pass

Both work items are correctly implemented. All 21 tests pass. No critical or significant findings.

---

## Critical Findings

None.

---

## Significant Findings

None.

---

## Minor Findings

### M1: Pre-existing `@pytest.mark.asyncio` decorators not cleaned up by WI-200 test additions

- **File**: `tests/test_world_state_manager.py:43, 129, 158, 201, 231, 255, 266, 318, 338, 372, 400, 437, 468`
- **Issue**: Thirteen methods in `TestWorldStateManager` carry `@pytest.mark.asyncio` decorators. The project constraint (CLAUDE.md, `pyproject.toml` `asyncio_mode=auto`) states these are unnecessary and may cause warnings. The four new tests added by WI-200 correctly omit the decorator, but no cleanup was done to the surrounding context. WI-200 added code into a class that already violated the constraint; the violation is not new to this cycle but the cycle touched the file.
- **Suggested fix**: Remove all `@pytest.mark.asyncio` decorators from `TestWorldStateManager`. With `asyncio_mode=auto`, `async def` methods are auto-detected without the decorator.

### M2: WI-200 notes spec format does not match implementation

- **File**: `specs/plan/notes/200.md:24`
- **Issue**: The notes file shows `f"Notification [{ntype}]: {event.message or ''}"` — using bare brackets without `type=` and referencing a non-existent field `event.message`. The implementation correctly uses `f"Notification [type={ntype}]: {event.notification_message or ''}"`, which matches the acceptance criterion example and the real field name. The notes file is now stale and misleading.
- **Suggested fix**: Update `specs/plan/notes/200.md` line 24 to match the actual implementation: `f"Notification [type={ntype}]: {event.notification_message or ''}"`.

---

## Cross-Cutting Correctness

### WI-199: end_turn behavior

The `end_turn` guard is added in both required locations:

- `src/hamlet/inference/engine.py:366` — `if event.stop_reason in ("tool", "stop", "end_turn"):`
- `src/hamlet/world_state/manager.py:883` — `if event.stop_reason in ("tool", "stop", "end_turn"):`

Tool eviction is correctly scoped to `stop_reason == "tool"` only (engine.py:367). `end_turn` and `stop` reach the IDLE-marking block without touching `pending_tools` or `active_tools`. This is correct.

The `manager.py` Stop branch collects agent IDs under the lock (line 888-891), releases it, then calls `update_agent` per agent (line 892-893). This is the correct pattern for avoiding re-entrant lock acquisition on `asyncio.Lock`.

### WI-200: notification_type differentiation

The branch at `manager.py:874-879` reads `event.notification_type`, defaults `None` to `"generic"`, and branches on whether the effective type is `"generic"`. Non-generic types produce `"Notification [type={ntype}]: ..."` and generic/None fall back to `"Notification: ..."`. Both the None-fallback and the explicit-`"generic"` case are covered by separate tests. The logic is correct and matches all three AC criteria.

---

## Test Coverage

### WI-199 — `tests/test_inference_engine.py`

`test_stop_end_turn_reason_marks_idle` (line 96):
- Asserts agent is marked IDLE via `update_agent.assert_awaited_once_with(agent_id, state=AgentState.IDLE)`.
- Asserts pending tools are NOT evicted (line 116: `assert pt_key in engine._state.pending_tools`).
- Does not assert `active_tools` remains unchanged, but this is implicitly guaranteed by the pending-tool assertion — if eviction ran, the tool would be gone.
- Coverage is adequate for the acceptance criteria.

### WI-200 — `tests/test_world_state_manager.py`

Four new tests cover:
1. Non-generic types produce differentiated summaries (parametrized: "warning", "error").
2. Explicit `"generic"` type falls back to plain format.
3. `None` type falls back to plain format.

No error path exists for this branch (it has no side effects beyond string formatting), so only happy-path and variant-input tests are required. Coverage is complete.

---

## Unmet Acceptance Criteria

None.

All criteria for WI-199 and WI-200 are satisfied by the implementation.

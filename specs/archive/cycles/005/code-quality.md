# Code Quality Review — Cycle 5 (WI-208 through WI-212)

## Verdict: Pass

One significant finding was found and fixed inline during rework (AgentUpdater ZOMBIE guard). Two minor findings were also fixed inline. All acceptance criteria are met post-rework.

## Critical Findings

None.

## Significant Findings

### S1: `AgentUpdater` overwrites `AgentState.ZOMBIE` with `IDLE` on every tick — FIXED

- **File**: `src/hamlet/simulation/agent_updater.py:38`
- **Issue**: `update_agents()` had no guard for `AgentState.ZOMBIE`. All agents loaded from persistence start as ZOMBIE with old `last_seen` timestamps, so on tick 1 every agent got `new_state = IDLE`, overwriting ZOMBIE. Then the inference engine re-marked them ZOMBIE. The two subsystems fought each other on every tick.
- **Fix**: ZOMBIE guard added — `if agent.state == AgentState.ZOMBIE: continue` at the start of the loop body. ZOMBIE lifecycle is now exclusively owned by `AgentInferenceEngine._update_zombie_states()`. Test `test_zombie_agent_is_skipped` added to `tests/test_agent_updater.py` to enforce the invariant.

## Minor Findings

### M1: `ZOMBIE_THRESHOLD_SECONDS` class variable was a misleading dead name — FIXED

- **File**: `src/hamlet/inference/engine.py`
- **Fix**: `ZOMBIE_THRESHOLD_SECONDS` class variable removed. The live threshold is `self._zombie_threshold_seconds` (constructor parameter, default 300). One test referencing the removed constant updated to use `engine._zombie_threshold_seconds` instead.

### M2: `test_agent_updater.py` had no ZOMBIE coverage — FIXED

- **Fix**: `test_zombie_agent_is_skipped` added to `tests/test_agent_updater.py`. Passes a ZOMBIE agent with old `last_seen` to `update_agents()`, asserts `update_agent` is never called.

## Significant Findings Addressed During Rework

- S1 (AgentUpdater ZOMBIE guard): Added `if agent.state == AgentState.ZOMBIE: continue` in `agent_updater.py`. Added `test_zombie_agent_is_skipped` in `test_agent_updater.py`.
- M1 (`ZOMBIE_THRESHOLD_SECONDS`): Removed dead class variable from `engine.py`. Updated `test_zombie_detection.py` to reference `engine._zombie_threshold_seconds`.
- M2 (missing ZOMBIE test): Added `test_zombie_agent_is_skipped`.

## Unmet Acceptance Criteria

None.

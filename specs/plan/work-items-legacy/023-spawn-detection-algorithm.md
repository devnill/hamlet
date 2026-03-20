# 023: Spawn Detection Algorithm

## Objective
Implement spawn detection heuristics that infer when a new agent has been spawned based on concurrent tool usage patterns.

## Acceptance Criteria
- [ ] `_detect_spawn(event, state)` async method detects spawns
- [ ] First event in new session creates spawn result with `parent_id=None`
- [ ] PreToolUse while session has active tools creates spawn with parent inference
- [ ] `_get_primary_agent(session_id)` helper finds parent agent
- [ ] `_handle_pre_tool_use` calls spawn detection and records pending tools
- [ ] New sessions added to state when first seen

## File Scope
- `src/hamlet/inference/engine.py` (modify)
- `tests/test_spawn_detection.py` (create)

## Dependencies
- Depends on: 022
- Blocks: none

## Implementation Notes
Spawn detection uses concurrent PreToolUse events and session tracking. Primary agent is one with most recent activity. Store pending tools in inference state.

## Complexity
Medium
# 032: Create WorldState Container

## Objective
Implement the WorldState container class holding all entity maps and event log.

## Acceptance Criteria
- [ ] File `src/hamlet/world_state/state.py` exists
- [ ] `WorldState` class with `projects`, `sessions`, `agents`, `villages`, `structures` dict attributes
- [ ] `EventLogEntry` dataclass with id, timestamp, session_id, project_id, hook_type, tool_name, summary fields
- [ ] `event_log` list attribute for chronological events
- [ ] Module imports all types from `world_state.types`

## File Scope
- `src/hamlet/world_state/state.py` (create)

## Dependencies
- Depends on: 031
- Blocks: 034

## Implementation Notes
WorldState is a simple container. Entity maps are keyed by ID strings. Event log is ordered chronologically.

## Complexity
Low
# 068: Reactive State Updates

## Objective
Implement periodic state polling that updates all reactive properties from World State.

## Acceptance Criteria
- [ ] `_update_state()` async method polls World State at 10 Hz
- [ ] Updates StatusBar reactive properties: `agent_count`, `structure_count`, `project_name`, `viewport_pos`
- [ ] Updates EventLog `events` property from `world_state.get_event_log(limit=100)`
- [ ] Updates viewport center if in follow mode
- [ ] Handles empty World State gracefully (no villages, no agents)
- [ ] All updates are non-blocking (no UI freeze)
- [ ] State polling runs on interval separate from render loop

## File Scope
- `src/hamlet/tui/app.py` (modify)

## Dependencies
- Depends on: 061, 063, 064, 065
- Blocks: none

## Implementation Notes
Use `set_interval(1/10, self._update_state)` for 10 Hz polling. The render loop runs at 30 Hz independently. State polling queries World State for entities in the current viewport bounds and updates reactive properties. Textual automatically triggers re-render when reactives change.

## Complexity
Medium
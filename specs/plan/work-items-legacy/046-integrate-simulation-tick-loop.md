# 046: Integrate Simulation Components into Tick Loop

## Objective
Connect all simulation components into the SimulationEngine tick loop.

## Acceptance Criteria
- [ ] `SimulationEngine._tick()` calls all update components in sequence
- [ ] Retrieves villages, then agents and structures per village
- [ ] Calls `agent_updater.update_agents()`
- [ ] Calls `structure_updater.update_structures()`
- [ ] Calls `expansion_manager.process_expansion()` once per tick
- [ ] Calls `animation_manager.advance_frames()`
- [ ] Each component call wrapped in try/except
- [ ] Order: agent updates, structure updates, expansion check, animation advance

## File Scope
- `src/hamlet/simulation/engine.py` (modify)

## Dependencies
- Depends on: 041, 042, 043, 044, 045
- Blocks: none

## Implementation Notes
Tick loop is single async task. WorldStateManager handles all internal locking. Errors in one component do not prevent others from running.

## Complexity
Medium
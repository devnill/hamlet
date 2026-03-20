# 046: Integrate Simulation Components into Tick Loop

## Objective
Connect all simulation components into SimulationEngine tick loop.

## Acceptance Criteria
- [ ] `SimulationEngine._tick()` calls all update components in sequence
- [ ] Retrieves villages, agents, structures from world_state
- [ ] Calls `agent_updater.update_agents()`
- [ ] Calls `structure_updater.update_structures()`
- [ ] Calls `expansion_manager.process_expansion()` once per tick
- [ ] Calls `animation_manager.advance_frames()`
- [ ] Each component wrapped in try/except, errors logged but don't crash simulation

## File Scope
- `src/hamlet/simulation/engine.py` (modify)

## Dependencies
- Depends on: 041, 042, 043, 044, 045
- Blocks: none

## Implementation Notes
Order: agent updates → structure updates → expansion check → animation advance. All state mutations go through WorldStateManager.

## Complexity
Medium
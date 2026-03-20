# 036: Implement Agent CRUD with Position Assignment

## Objective
Implement agent creation, update, and position assignment with spiral search algorithm.

## Acceptance Criteria
- [ ] `get_or_create_agent(session_id, parent_id)` returns existing or new Agent
- [ ] `_find_spawn_position(village, parent, occupied)` implements spiral search
- [ ] Spawn position within 3 cells of parent or village center
- [ ] `update_agent(agent_id, **fields)` updates agent and queues persistence
- [ ] `get_agent(agent_id)`, `get_agents_by_session(session_id)`, `get_agents_by_village(village_id)`
- [ ] New agents start with state=ACTIVE, type=GENERAL, color="white"

## File Scope
- `src/hamlet/world_state/manager.py` (modify)

## Dependencies
- Depends on: 035
- Blocks: 037

## Implementation Notes
Position uniqueness enforced by PositionGrid. Spiral search finds nearest unoccupied cell.

## Complexity
High
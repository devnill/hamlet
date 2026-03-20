# 036: Implement Agent CRUD with Position Assignment

## Objective
Implement agent creation, update, and position assignment with spiral search.

## Acceptance Criteria
- [ ] `get_or_create_agent(session_id, parent_id)` returns or creates agent
- [ ] `_find_spawn_position(village, parent, occupied)` implements spiral search
- [ ] Position uniqueness enforced via grid
- [ ] `update_agent(agent_id, **fields)` updates and queues persistence
- [ ] `get_agents_by_session`, `get_agents_by_village` query methods

## File Scope
- `src/hamlet/world_state/manager.py` (modify)

## Dependencies
- Depends on: 035
- Blocks: 037

## Implementation Notes
Spiral search finds empty cell within MAX_SPAWN_RADIUS (default 3) of parent or village center. New agents start with GENERAL type, white color, ACTIVE state.

## Complexity
High
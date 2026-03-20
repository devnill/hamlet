# 035: Implement Project, Session, and Village CRUD

## Objective
Implement CRUD operations for projects, sessions, and villages.

## Acceptance Criteria
- [ ] `get_or_create_project(project_id, name)` returns or creates project with village
- [ ] `get_or_create_session(session_id, project_id)` returns or creates session
- [ ] `get_village(village_id)` and `get_village_by_project(project_id)`
- [ ] `_expand_village_bounds(village, position)` updates village bounds
- [ ] All public methods are async and acquire lock

## File Scope
- `src/hamlet/world_state/manager.py` (modify)

## Dependencies
- Depends on: 034
- Blocks: 036

## Implementation Notes
Projects automatically create villages. Village center starts at (0,0). Bounds expand as agents move.

## Complexity
Medium
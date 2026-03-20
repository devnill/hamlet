# 035: Implement Project, Session, and Village CRUD

## Objective
Implement CRUD operations for projects, sessions, and villages including village bounds management.

## Acceptance Criteria
- [ ] `get_or_create_project(project_id, name)` returns existing or new Project
- [ ] Creates associated Village for new projects
- [ ] `get_or_create_session(session_id, project_id)` returns existing or new Session
- [ ] `get_village(village_id)` and `get_village_by_project(project_id)`
- [ ] `_expand_village_bounds(village, position)` private method
- [ ] All public methods async and lock-protected

## File Scope
- `src/hamlet/world_state/manager.py` (modify)

## Dependencies
- Depends on: 034
- Blocks: 036

## Implementation Notes
Village center starts at (0, 0). Bounds expand as agents move. Queue persistence writes after state changes.

## Complexity
Medium
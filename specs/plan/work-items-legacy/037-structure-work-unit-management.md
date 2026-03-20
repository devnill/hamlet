# 037: Implement Structure and Work Unit Management

## Objective
Implement structure CRUD, work unit accumulation, and stage progression with material upgrades.

## Acceptance Criteria
- [ ] `create_structure(village_id, type, position)` creates new Structure
- [ ] `update_structure(structure_id, **fields)` updates and queues persistence
- [ ] `get_structure(id)`, `get_structures_by_village(village_id)`
- [ ] `add_work_units(agent_id, structure_type, units)` adds to agent total and structure
- [ ] Structure stage advances when work_units >= threshold
- [ ] Material evolves: wood → stone at stage 2, stone → brick at stage 3
- [ ] `STAGE_THRESHOLDS` and `MATERIAL_STAGES` constants defined

## File Scope
- `src/hamlet/world_state/manager.py` (modify)

## Dependencies
- Depends on: 036
- Blocks: none

## Implementation Notes
Thresholds: HOUSE=[100,500,1000], WORKSHOP=[150,750,1500], etc. Work units reset after stage advancement.

## Complexity
High
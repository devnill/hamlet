# 037: Implement Structure and Work Unit Management

## Objective
Implement structure CRUD, work unit accumulation, and stage progression.

## Acceptance Criteria
- [ ] `create_structure(village_id, type, position)` creates structure
- [ ] `update_structure(structure_id, **fields)` updates structure
- [ ] `add_work_units(agent_id, structure_type, units)` accumulates work and advances stages
- [ ] `STAGE_THRESHOLDS` and `MATERIAL_STAGES` constants define progression
- [ ] Stage advancement updates material (wood → stone → brick)

## File Scope
- `src/hamlet/world_state/manager.py` (modify)

## Dependencies
- Depends on: 036
- Blocks: none

## Implementation Notes
Work units from tool calls accumulate per structure type. Threshold determines stage advancement. Materials evolve at stage boundaries.

## Complexity
High
# 043: Implement Structure Progression System

## Objective
Implement structure evolution logic advancing construction stages based on work units.

## Acceptance Criteria
- [ ] File `src/hamlet/simulation/structure_updater.py` exists
- [ ] `StructureUpdater` class with `__init__(config)`
- [ ] `STRUCTURE_RULES` constant defines thresholds and materials per structure type
- [ ] `async update_structures(structures, world_state)` method
- [ ] Skips structures with stage >= 3 (complete)
- [ ] Increments stage when work_units >= threshold
- [ ] Updates material at stage advancement
- [ ] Defines all structure types: HOUSE, WORKSHOP, LIBRARY, FORGE, TOWER, ROAD, WELL

## File Scope
- `src/hamlet/simulation/structure_updater.py` (create)

## Dependencies
- Depends on: 041
- Blocks: none

## Implementation Notes
Material progression: stage 0-1 = wood, stage 2 = stone, stage 3 = brick. Thresholds defined per structure type.

## Complexity
Low
# 045: Implement Village Expansion and Road Building

## Objective
Implement village expansion logic detecting crowding and creating roads to new settlements.

## Acceptance Criteria
- [ ] File `src/hamlet/simulation/expansion.py` exists
- [ ] `ExpansionManager` class with `__init__(config)`
- [ ] `check_village_expansion(village, agents, all_villages)` returns expansion site Position or None
- [ ] Expansion triggers when agent count >= expansion_threshold (default 20)
- [ ] `_is_clear_site(position, all_villages, min_distance)` checks for village conflicts
- [ ] `create_road_between(world_state, village_id, start, end)` uses Bresenham's line algorithm
- [ ] Road segments created with stage=3, material=stone

## File Scope
- `src/hamlet/simulation/expansion.py` (create)

## Dependencies
- Depends on: 041, World State module
- Blocks: none

## Implementation Notes
Expansion site search: 20-50 cells from village center, check every 15 degrees. Roads are stone structures.

## Complexity
High
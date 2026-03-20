# 045: Implement Village Expansion and Road Building

## Objective
Implement village expansion logic that detects crowding and creates roads to new settlements.

## Acceptance Criteria
- [ ] File `src/hamlet/simulation/expansion.py` exists
- [ ] `ExpansionManager.__init__(config)` constructor
- [ ] `check_village_expansion(village, agents, all_villages)` returns Position or None
- [ ] Expands when agent count >= config.expansion_threshold (default 20)
- [ ] Searches for expansion site 20-50 cells from village center
- [ ] `_is_clear_site(pos, all_villages)` checks no nearby villages
- [ ] `create_road_between(world_state, village_id, start, end)` uses Bresenham's algorithm
- [ ] Road segments created with stage=3, material="stone"

## File Scope
- `src/hamlet/simulation/expansion.py` (create)

## Dependencies
- Depends on: 041
- Blocks: none

## Implementation Notes
Expansion site at every 15 degrees around center. Roads use Bresenham's line algorithm. Duplicate roads prevented by tracking created connections.

## Complexity
High
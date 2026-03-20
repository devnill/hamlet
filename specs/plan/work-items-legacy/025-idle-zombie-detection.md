# 025: Idle and Zombie Detection

## Objective
Implement idle/zombie detection that marks agents inactive beyond threshold with zombie color blending.

## Acceptance Criteria
- [ ] `ZOMBIE_THRESHOLD_SECONDS = 300` constant
- [ ] `_check_zombie(agent_id)` compares last_seen against threshold
- [ ] `_update_zombie_states()` async method iterates all agents
- [ ] `get_display_color(agent)` blends base color with green for zombies
- [ ] `blend_color(base, overlay, ratio)` helper function
- [ ] Simulation module calls `_update_zombie_states()` periodically

## File Scope
- `src/hamlet/inference/engine.py` (modify)
- `src/hamlet/inference/colors.py` (create)
- `tests/test_zombie_detection.py` (create)

## Dependencies
- Depends on: 022
- Blocks: none

## Implementation Notes
Zombie threshold is 5 minutes (configurable). Color blending for MVP can be simplified to alternate between base and green.

## Complexity
Low
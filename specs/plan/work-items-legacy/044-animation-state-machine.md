# 044: Implement Animation State Machine

## Objective
Implement animation state management for agents showing activity and zombie pulse effects.

## Acceptance Criteria
- [ ] File `src/hamlet/simulation/animation.py` exists
- [ ] `AnimationState` dataclass with animation_type, current_frame, frame_count
- [ ] `AnimationManager` class with `get_animation_state(agent)`, `get_animation_symbol(state)`, `get_animation_color(agent, state, time)`
- [ ] Active agents show spin animation (`-`, `\`, `|`, `/`)
- [ ] Idle agents show static `@`
- [ ] Zombie agents pulse between base color and green at 0.5Hz
- [ ] `advance_frames(agents, delta_ticks)` increments frame counters

## File Scope
- `src/hamlet/simulation/animation.py` (create)

## Dependencies
- Depends on: World State module (Agent type)
- Blocks: none

## Implementation Notes
Spin animation is 4Hz (4 frames per second). Frame counters stored per-agent in internal dict.

## Complexity
Medium
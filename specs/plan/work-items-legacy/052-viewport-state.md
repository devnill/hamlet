# 052: Viewport State Dataclass

## Objective
Define `ViewportState` dataclass tracking viewport center, size, follow mode, and follow target.

## Acceptance Criteria
- [ ] File `src/hamlet/viewport/state.py` exists
- [ ] `ViewportState` dataclass with `center: Position`, `size: Size`, `follow_mode: "center" | "free"`, `follow_target: str | None`
- [ ] Default viewport size is 80x24 (standard terminal)
- [ ] Default follow_mode is "center"
- [ ] Default follow_target is None
- [ ] `set_center(position: Position) -> None` method switches to free mode
- [ ] `scroll(delta_x: int, delta_y: int) -> None` method switches to free mode and updates center
- [ ] `set_follow_target(agent_id: str) -> None` method switches to center mode with target

## File Scope
- `src/hamlet/viewport/state.py` (create)

## Dependencies
- Depends on: 051
- Blocks: 054, 055

## Implementation Notes
Scroll operations automatically switch to "free" mode. Setting a follow target switches to "center" mode. The state is mutable for updates from the simulation.

## Complexity
Low
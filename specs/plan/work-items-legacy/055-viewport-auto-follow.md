# 055: ViewportManager Auto-Follow and Visibility Queries

## Objective
Implement auto-follow logic and entity visibility query methods in ViewportManager.

## Acceptance Criteria
- [ ] `scroll(delta_x: int, delta_y: int) -> None` method scrolls viewport (switches to free mode)
- [ ] `set_center(position: Position) -> None` method sets explicit center (switches to free mode)
- [ ] `auto_follow(agent_id: str) -> None` method enables follow mode for agent
- [ ] `async update() -> None` method updates center if in follow mode
- [ ] `async get_agents_in_view() -> List[str]` method returns visible agent IDs
- [ ] `async get_structures_in_view() -> List[str]` method returns visible structure IDs
- [ ] Follow mode: if agent no longer exists, revert to village center
- [ ] Free mode: scroll operations do not auto-update center

## File Scope
- `src/hamlet/viewport/manager.py` (modify)

## Dependencies
- Depends on: 054
- Blocks: 056

## Implementation Notes
Auto-follow checks if the followed agent still exists in World State. If not, it clears follow_target and centers on the primary village. The update() method is called each frame by the TUI when in follow mode.

## Complexity
Medium
# 033: Implement Position Grid Index

## Objective
Create sparse grid index for fast position lookup and uniqueness checking.

## Acceptance Criteria
- [ ] `src/hamlet/world_state/grid.py` exists
- [ ] `PositionGrid` class with `occupy`, `vacate`, `is_occupied`, `get_entity_at`, `get_occupied_positions` methods
- [ ] Uses `dict[Position, str]` for storage

## File Scope
- `src/hamlet/world_state/grid.py` (create)

## Dependencies
- Depends on: 031
- Blocks: 036

## Implementation Notes
Position must be hashable. Use `Position` from types module. `occupy` raises `ValueError` if position taken. `vacate` is idempotent.

## Complexity
Low
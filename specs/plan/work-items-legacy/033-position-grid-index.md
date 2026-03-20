# 033: Implement Position Grid Index

## Objective
Create a sparse grid index for position uniqueness checking and fast visibility queries.

## Acceptance Criteria
- [ ] File `src/hamlet/world_state/grid.py` exists
- [ ] `PositionGrid` class with `occupy`, `vacate`, `is_occupied`, `get_entity_at`, `get_occupied_positions` methods
- [ ] Position must be hashable (frozen=True or custom `__hash__`)
- [ ] `occupy(position, entity_id)` raises ValueError if position already occupied
- [ ] `vacate` is idempotent

## File Scope
- `src/hamlet/world_state/grid.py` (create)

## Dependencies
- Depends on: 031
- Blocks: 036

## Implementation Notes
Internal storage uses `dict[Position, str]`. No persistence — in-memory only.

## Complexity
Low
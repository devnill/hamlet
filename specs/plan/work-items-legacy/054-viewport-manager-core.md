# 054: ViewportManager Core Operations

## Objective
Implement `ViewportManager` class with core viewport operations: initialization, resize, world-to-screen translation, and visibility checks.

## Acceptance Criteria
- [ ] File `src/hamlet/viewport/manager.py` exists
- [ ] `ViewportManager` class with `__init__(world_state: WorldStateManager)`
- [ ] `async initialize() -> None` sets center to primary village center
- [ ] `world_to_screen(world_pos: Position) -> Position` method
- [ ] `screen_to_world(screen_pos: Position) -> Position` method
- [ ] `is_visible(world_pos: Position) -> bool` method
- [ ] `get_visible_bounds() -> BoundingBox` method
- [ ] `resize(width: int, height: int) -> None` method
- [ ] `get_viewport_state() -> ViewportState` method returns current state snapshot
- [ ] Uses `SpatialIndex` for visibility queries

## File Scope
- `src/hamlet/viewport/manager.py` (create)

## Dependencies
- Depends on: 051, 052, 053
- Blocks: 055, 056

## Implementation Notes
ViewportManager holds a reference to WorldStateManager for reading entity positions. It maintains internal SpatialIndex updated when entities move. Initialize reads all villages and centers on the first one.

## Complexity
Medium
# 051: Coordinate Types and Translation

## Objective
Define coordinate system types (Position, BoundingBox, Size) and implement coordinate translation functions.

## Acceptance Criteria
- [ ] File `src/hamlet/viewport/coordinates.py` exists
- [ ] `Position` dataclass with `x: int`, `y: int` fields
- [ ] `Size` dataclass with `width: int`, `height: int` fields
- [ ] `BoundingBox` dataclass with `min_x`, `min_y`, `max_x`, `max_y` fields
- [ ] `world_to_screen(world_pos, viewport_center, viewport_size) -> Position` function
- [ ] `screen_to_world(screen_pos, viewport_center, viewport_size) -> Position` function
- [ ] `is_visible(world_pos, viewport_bounds) -> bool` function
- [ ] `get_visible_bounds(viewport_center, viewport_size) -> BoundingBox` function
- [ ] All coordinates are integers (no sub-cell positioning)

## File Scope
- `src/hamlet/viewport/coordinates.py` (create)

## Dependencies
- Depends on: none
- Blocks: 052, 053, 054

## Implementation Notes
World coordinates are global with origin (0,0) at first village center. X increases east (right), Y increases south (down). Screen coordinates are viewport-relative: top-left is (0,0). Translation formulas: screen_x = world_x - center_x + width//2, screen_y = world_y - center_y + height//2.

## Complexity
Low
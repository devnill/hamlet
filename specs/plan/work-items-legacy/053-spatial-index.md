# 053: Spatial Index for Visibility Queries

## Objective
Implement `SpatialIndex` class for fast entity visibility queries without iterating all entities.

## Acceptance Criteria
- [ ] File `src/hamlet/viewport/spatial_index.py` exists
- [ ] `SpatialIndex` class with `__init__(cell_size: int = 50)`
- [ ] `update(entity_id: str, position: Position) -> None` method updates entity position in grid
- [ ] `remove(entity_id: str) -> None` method removes entity from index
- [ ] `query(bounds: BoundingBox) -> List[str]` method returns entity IDs in bounding box
- [ ] `clear() -> None` method clears all entities
- [ ] Internal grid uses cell-based hashing for O(1) updates
- [ ] Query complexity is O(cells in bounds) not O(total entities)

## File Scope
- `src/hamlet/viewport/spatial_index.py` (create)

## Dependencies
- Depends on: 051
- Blocks: 054

## Implementation Notes
The spatial index divides the world into cells (default 50x50). Each entity is placed in exactly one cell based on its position. Query iterates over cells that intersect the bounding box. This avoids checking every entity for visibility.

## Complexity
Medium
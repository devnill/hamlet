# 056: Viewport Package Exports

## Objective
Create `src/hamlet/viewport/__init__.py` with public exports for the viewport module.

## Acceptance Criteria
- [ ] File `src/hamlet/viewport/__init__.py` exists
- [ ] Exports `Position`, `Size`, `BoundingBox` from `coordinates`
- [ ] Exports `ViewportState` from `state`
- [ ] Exports `SpatialIndex` from `spatial_index`
- [ ] Exports `ViewportManager` from `manager`
- [ ] All exports are in `__all__` list
- [ ] Package can be imported as `from hamlet.viewport import ViewportManager, Position, BoundingBox`

## File Scope
- `src/hamlet/viewport/__init__.py` (create)

## Dependencies
- Depends on: 051, 052, 053, 054, 055
- Blocks: none

## Implementation Notes
This is the public interface for the viewport module. Import all types and classes from submodules and re-export them.

## Complexity
Low
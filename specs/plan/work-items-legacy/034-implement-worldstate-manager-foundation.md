# 034: Implement WorldStateManager Foundation

## Objective
Create `WorldStateManager` class with initialization and state restoration from Persistence.

## Acceptance Criteria
- [ ] `src/hamlet/world_state/manager.py` exists
- [ ] `WorldStateManager.__init__` takes `persistence`, creates `asyncio.Lock`, `WorldState`, `PositionGrid`
- [ ] `async load_from_persistence()` loads all entities and rebuilds grid
- [ ] All public methods acquire lock before modifying state

## File Scope
- `src/hamlet/world_state/manager.py` (create)

## Dependencies
- Depends on: 031, 032, 033
- Blocks: 035, 036, 037

## Implementation Notes
Write-behind pattern: state changes queue writes to persistence. Persistence interface provides `load_state()` and `queue_write()`.

## Complexity
Medium
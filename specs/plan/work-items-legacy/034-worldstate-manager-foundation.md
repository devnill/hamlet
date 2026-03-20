# 034: Implement WorldStateManager Foundation

## Objective
Create WorldStateManager with initialization, asyncio lock, and state restoration from Persistence.

## Acceptance Criteria
- [ ] File `src/hamlet/world_state/manager.py` exists
- [ ] `WorldStateManager.__init__(persistence)` stores reference
- [ ] Creates `asyncio.Lock` for thread-safe access
- [ ] Creates `WorldState` instance
- [ ] Creates `PositionGrid` instance
- [ ] `async load_from_persistence()` restores all entities from database
- [ ] Rebuilds PositionGrid from loaded agent and structure positions

## File Scope
- `src/hamlet/world_state/manager.py` (create)

## Dependencies
- Depends on: 031, 032, 033
- Blocks: 035, 036, 037

## Implementation Notes
Persistence interface: `load_state()` returns `WorldStateData`. Write-behind pattern for saves.

## Complexity
Medium
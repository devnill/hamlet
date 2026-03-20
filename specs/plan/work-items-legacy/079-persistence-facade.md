# 079: Persistence Facade and Checkpoint

## Objective
Implement the main `Persistence` class that coordinates all persistence components.

## Acceptance Criteria
- [ ] File `src/hamlet/persistence/__init__.py` exports `Persistence`, `PersistenceConfig`, `WorldStateData`
- [ ] `Persistence` class with `__init__(config: PersistenceConfig)`
- [ ] `async start() -> None` initializes database, runs migrations, starts write queue
- [ ] `async stop() -> None` stops write queue and closes database
- [ ] `async load_state() -> WorldStateData` delegates to StateLoader
- [ ] `async save_<entity>(entity)` methods delegate to EntitySaver
- [ ] `async checkpoint() -> None` flushes write queue and runs WAL checkpoint
- [ ] `async close() -> None` is alias for stop()
- [ ] `get_default_db_path() -> Path` function returns `~/.hamlet/world.db`
- [ ] Creates `.hamlet` directory if it doesn't exist

## File Scope
- `src/hamlet/persistence/__init__.py` (create)
- `src/hamlet/persistence/facade.py` (create)

## Dependencies
- Depends on: 071, 072, 073, 074, 075, 076, 077, 078
- Blocks: none

## Implementation Notes
The Persistence facade is the main entry point. It holds DatabaseConnection, WriteQueue, WriteExecutor, StateLoader, EntitySaver, and EventLogManager. Start creates the write loop task, stop cancels it and waits for completion. Checkpoint drains the queue and runs `PRAGMA wal_checkpoint`.

## Complexity
Medium
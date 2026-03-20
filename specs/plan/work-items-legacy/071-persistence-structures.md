# 071: Persistence Data Structures

## Objective
Define dataclasses and types for persistence layer: WriteOperation, PersistenceConfig, WorldStateData.

## Acceptance Criteria
- [ ] File `src/hamlet/persistence/types.py` exists
- [ ] `WriteOperation` dataclass with `entity_type`, `entity_id`, `operation`, `data` fields
- [ ] `PersistenceConfig` dataclass with `db_path`, `write_queue_size`, `checkpoint_interval` fields and defaults
- [ ] `WorldStateData` dataclass with `projects`, `sessions`, `villages`, `agents`, `structures`, `metadata` fields
- [ ] `entity_type` is Literal union: "project", "session", "agent", "structure", "village", "event_log"
- [ ] `operation` is Literal: "insert", "update", "delete"
- [ ] Default `db_path` is `~/.hamlet/world.db`
- [ ] Default `write_queue_size` is 1000
- [ ] Default `checkpoint_interval` is 5.0 seconds

## File Scope
- `src/hamlet/persistence/types.py` (create)

## Dependencies
- Depends on: none
- Blocks: 072, 073, 074, 075, 076, 077, 078, 079

## Implementation Notes
These types are the public interface for the persistence module. WriteOperation represents a queued write. PersistenceConfig is passed to Persistence constructor. WorldStateData is the result of loading state from disk.

## Complexity
Low
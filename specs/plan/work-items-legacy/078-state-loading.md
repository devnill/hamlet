# 078: State Loading

## Objective
Implement loading all World State from database on startup.

## Acceptance Criteria
- [ ] File `src/hamlet/persistence/loader.py` exists
- [ ] `StateLoader` class with `__init__(db: DatabaseConnection)`
- [ ] `async load_state() -> WorldStateData` loads all entities from database
- [ ] Loads projects, sessions, villages, agents, structures, metadata tables
- [ ] Converts database rows to dataclass instances
- [ ] Parses JSON fields (agent_ids, config_json)
- [ ] Parses ISO timestamps to datetime objects
- [ ] Returns `WorldStateData` with all lists populated
- [ ] Handles empty database gracefully (returns empty lists)

## File Scope
- `src/hamlet/persistence/loader.py` (create)

## Dependencies
- Depends on: 071, 072
- Blocks: 079

## Implementation Notes
Loading reads all tables and converts rows to dataclasses. Position fields (x, y) are stored as separate columns and combined into Position objects. Metadata is stored as key-value pairs and returned as dict.

## Complexity
Medium
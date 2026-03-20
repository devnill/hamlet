# 072: Database Connection Management

## Objective
Implement async SQLite connection lifecycle with aiosqlite.

## Acceptance Criteria
- [ ] File `src/hamlet/persistence/connection.py` exists
- [ ] `DatabaseConnection` class wraps `aiosqlite.Connection`
- [ ] `async __aenter__()` and `async __aexit__()` for context manager protocol
- [ ] `async execute(sql, params)` method executes a query
- [ ] `async executemany(sql, params_list)` method executes batch queries
- [ ] `async fetchone()` and `async fetchall()` methods return query results
- [ ] `async begin_transaction()` and `async commit()` for explicit transactions
- [ ] Connection opened with `WAL` mode for concurrent read/write support
- [ ] Connection uses `aiosqlite.connect(db_path)` with isolation level None

## File Scope
- `src/hamlet/persistence/connection.py` (create)

## Dependencies
- Depends on: 071
- Blocks: 073, 077, 078

## Implementation Notes
WAL mode (`PRAGMA journal_mode=WAL`) allows concurrent reads while writing. Isolation level None means we manage transactions explicitly. The context manager ensures proper cleanup on exit.

## Complexity
Low
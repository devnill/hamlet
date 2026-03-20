# 077: Event Log Operations

## Objective
Implement event log append with size cap and pruning.

## Acceptance Criteria
- [ ] File `src/hamlet/persistence/event_log.py` exists
- [ ] `EventLogManager` class with `__init__(db: DatabaseConnection, max_entries: int = 10000)`
- [ ] `async append(entry: EventLogEntry) -> None` inserts new event log entry
- [ ] After insert, prunes entries beyond `max_entries`
- [ ] Pruning query: `DELETE FROM event_log WHERE id < (SELECT id FROM event_log ORDER BY id DESC LIMIT 1 OFFSET ?)`
- [ ] Event log stores: timestamp, session_id, project_id, hook_type, tool_name, summary
- [ ] Timestamp stored as ISO 8601 string
- [ ] Tool name is nullable (for Notification events)

## File Scope
- `src/hamlet/persistence/event_log.py` (create)

## Dependencies
- Depends on: 071, 072
- Blocks: none

## Implementation Notes
The event log grows with each hook event. We cap it at 10,000 entries. Each append also checks if pruning is needed. The pruning uses a subquery to find the cutoff ID and deletes older entries.

## Complexity
Low
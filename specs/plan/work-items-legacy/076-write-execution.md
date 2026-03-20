# 076: Write Execution

## Objective
Implement the write execution logic that processes WriteOperation batches and executes SQL.

## Acceptance Criteria
- [ ] File `src/hamlet/persistence/writer.py` exists
- [ ] `WriteExecutor` class with `__init__(db: DatabaseConnection)`
- [ ] `async execute_batch(operations: List[WriteOperation]) -> None` processes batch in transaction
- [ ] `_execute_write(cursor, op: WriteOperation)` method executes single operation
- [ ] Handles all entity types: project, session, agent, structure, village, event_log
- [ ] Uses `INSERT OR REPLACE` for upsert operations
- [ ] Batch is atomic: all succeed or all fail (transaction)
- [ ] Logs errors for failed batches (does not raise, per guiding principle 7)
- [ ] Formats timestamps as ISO 8601 strings
- [ ] Serializes JSON fields (agent_ids in session, config_json in project)

## File Scope
- `src/hamlet/persistence/writer.py` (create)

## Dependencies
- Depends on: 071
- Blocks: none

## Implementation Notes
The WriteExecutor takes a batch of WriteOperations and executes them in a single transaction. For each operation, it determines the entity type and calls the appropriate INSERT statement. Error handling logs but doesn't propagate — writes are best-effort.

## Complexity
Medium
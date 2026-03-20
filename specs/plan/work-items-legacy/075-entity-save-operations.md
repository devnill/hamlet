# 075: Entity Save Operations

## Objective
Implement save methods for each entity type that queue write operations.

## Acceptance Criteria
- [ ] File `src/hamlet/persistence/saver.py` exists
- [ ] `EntitySaver` class with `__init__(queue: WriteQueue)`
- [ ] `async save_project(project: Project) -> None` queues project write
- [ ] `async save_session(session: Session) -> None` queues session write
- [ ] `async save_agent(agent: Agent) -> None` queues agent write
- [ ] `async save_structure(structure: Structure) -> None` queues structure write
- [ ] `async save_village(village: Village) -> None` queues village write
- [ ] Each method converts entity to dict and creates `WriteOperation` with operation="upsert"
- [ ] Uses `INSERT OR REPLACE` semantics (upsert)
- [ ] All methods are non-blocking (queue write, return immediately)

## File Scope
- `src/hamlet/persistence/saver.py` (create)

## Dependencies
- Depends on: 071, 074
- Blocks: none

## Implementation Notes
Each save method creates a WriteOperation with entity_type, entity_id, operation="upsert", and data dict. The actual SQL execution happens in the write loop. Methods are async but don't wait for write completion.

## Complexity
Low
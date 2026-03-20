# 074: Write-Behind Queue Infrastructure

## Objective
Implement async write queue that buffers state changes and writes them to disk in batches.

## Acceptance Criteria
- [ ] File `src/hamlet/persistence/queue.py` exists
- [ ] `WriteQueue` class with `__init__(max_size: int = 1000)`
- [ ] `async put(operation: WriteOperation) -> None` adds to queue (non-blocking, drops if full)
- [ ] `async get_batch(max_items: int = 100) -> List[WriteOperation]` retrieves batch
- [ ] `async start() -> None` creates background task for write loop
- [ ] `async stop() -> None` cancels write task and flushes remaining
- [ ] Background write loop processes queue continuously
- [ ] `_write_loop()` method is the async background task
- [ ] Queue drops writes when full (per guiding principle 7 — acceptable data loss)
- [ ] `qsize()` method returns current queue size

## File Scope
- `src/hamlet/persistence/queue.py` (create)

## Dependencies
- Depends on: 071
- Blocks: 075

## Implementation Notes
Use `asyncio.Queue` with maxsize for bounded queue. The write loop runs continuously, batching up to 100 writes at a time. When queue is full, `put_nowait` raises QueueFull, which we catch and drop. The write loop is started by `Persistence.start()`.

## Complexity
Medium
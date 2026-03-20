# 012: Sequence Generator

## Objective
Implement a thread-safe monotonic sequence generator for event processing.

## Acceptance Criteria
- [ ] File `src/hamlet/event_processing/sequence_generator.py` exists
- [ ] `SequenceGenerator` class with `next()` async method
- [ ] Sequence numbers start at 1 and increment by 1
- [ ] Concurrent calls return unique numbers (no duplicates)
- [ ] Uses `asyncio.Lock` for thread safety

## File Scope
- `src/hamlet/event_processing/sequence_generator.py` (create)
- `src/hamlet/event_processing/__init__.py` (modify)

## Dependencies
- Depends on: none
- Blocks: 014

## Implementation Notes
Internal counter starts at 0, returns 1 for first call. Lock ensures atomicity. No persistence — reset on restart.

## Complexity
Low
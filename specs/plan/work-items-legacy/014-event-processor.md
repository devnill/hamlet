# 014: Event Processor

## Objective
Implement the `EventProcessor` that orchestrates event pipeline: consuming from queue, normalizing, sequencing, validating, and routing to subscribers.

## Acceptance Criteria
- [ ] File `src/hamlet/event_processing/event_processor.py` exists
- [ ] `EventProcessor` class implements `EventRouter` interface
- [ ] `__init__` accepts `event_queue`, `world_state`, `agent_inference`, `persistence`
- [ ] `start()` begins consuming from queue
- [ ] `stop()` gracefully shuts down
- [ ] `process_event(raw)` returns `InternalEvent`
- [ ] Events routed to world_state, agent_inference, persistence, and subscribers
- [ ] Validation rejects events missing required fields

## File Scope
- `src/hamlet/event_processing/event_processor.py` (create)
- `src/hamlet/event_processing/__init__.py` (modify)

## Dependencies
- Depends on: 011, 012, 013
- Blocks: none

## Implementation Notes
Error handling follows graceful degradation: log errors, continue processing. Routing sends to all destinations concurrently where possible.

## Complexity
High
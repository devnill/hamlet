# 013: Event Router Interface

## Objective
Define the `EventRouter` interface for publish-subscribe pattern allowing modules to subscribe to events.

## Acceptance Criteria
- [ ] File `src/hamlet/event_processing/event_router.py` exists
- [ ] `EventCallback` type alias defined as `Callable[[InternalEvent], Awaitable[None]]`
- [ ] `EventRouter` abstract base class with `subscribe` and `unsubscribe` methods
- [ ] All methods are async

## File Scope
- `src/hamlet/event_processing/event_router.py` (create)
- `src/hamlet/event_processing/__init__.py` (modify)

## Dependencies
- Depends on: 011
- Blocks: 014

## Implementation Notes
Abstract interface. Concrete implementation in `EventProcessor`. Subscribers receive all processed events and can filter internally.

## Complexity
Low
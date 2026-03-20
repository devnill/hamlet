# 065: EventLog Widget

## Objective
Implement the event log widget showing recent events in chronological order.

## Acceptance Criteria
- [ ] File `src/hamlet/tui/event_log.py` exists
- [ ] `EventLog` class inherits from `textual.widgets.Static`
- [ ] Reactive property: `events` (list of EventLogEntry)
- [ ] Reactive property: `max_lines` (default 5)
- [ ] `render()` method formats events as "[HH:MM:SS] summary" lines
- [ ] Shows most recent `max_lines` events
- [ ] Auto-scrolls to show latest (most recent at bottom)
- [ ] Empty state shows "No events" message

## File Scope
- `src/hamlet/tui/event_log.py` (create)

## Dependencies
- Depends on: 061
- Blocks: 068

## Implementation Notes
Events are formatted with timestamp as HH:MM:SS. The main app updates `events` reactive property from World State. Textual automatically re-renders when reactive properties change. Display newest events at the bottom of the log.

## Complexity
Low
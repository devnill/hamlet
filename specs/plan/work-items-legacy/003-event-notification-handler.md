# 003: Event Notification Handler

## Objective
Implement the notification handler that receives `hamlet/event` notifications from hook scripts, validates payloads, and pushes validated events to the async queue.

## Acceptance Criteria
- [ ] File `src/hamlet/mcp_server/handlers.py` exists
- [ ] `register_handlers(server: Server, event_queue: asyncio.Queue)` function exists
- [ ] Handler registered for `hamlet/event` method via MCP SDK
- [ ] Handler validates payload using `validate_event`
- [ ] Valid events create `ValidatedEvent` and push to queue
- [ ] Invalid events logged at WARN level and discarded
- [ ] No exceptions propagate to MCP protocol layer

## File Scope
- `src/hamlet/mcp_server/handlers.py` (create)
- `src/hamlet/mcp_server/__init__.py` (modify)

## Dependencies
- Depends on: 001, 002
- Blocks: 004

## Implementation Notes
Handler must catch all exceptions and log them. Per guiding principle 7, the server must continue even if individual events fail.

## Complexity
Medium
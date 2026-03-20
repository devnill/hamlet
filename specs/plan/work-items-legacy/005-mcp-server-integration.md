# 005: MCPServer Integration

## Objective
Integrate MCP server components into application lifecycle, connecting MCPServer class with handlers and providing entry point.

## Acceptance Criteria
- [ ] `MCPServer.__init__()` creates asyncio.Queue and stores dependencies
- [ ] `MCPServer.start()` creates MCP Server instance and calls `register_handlers`
- [ ] `MCPServer.start()` spawns server run task using stdio_server context
- [ ] `MCPServer.stop()` cancels server task and cleans up
- [ ] `MCPServer.get_event_queue()` returns event queue
- [ ] Server runs as background task alongside TUI and simulation
- [ ] Module exports MCPServer class

## File Scope
- `src/hamlet/mcp_server/server.py` (modify)
- `src/hamlet/mcp_server/__init__.py` (modify)

## Dependencies
- Depends on: 001, 002, 003, 004
- Blocks: none

## Implementation Notes
Server runs as asyncio task. Graceful shutdown cancels task. Integration test verifies events can be queued and retrieved.

## Complexity
Medium
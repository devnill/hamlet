# 001: MCP Server Class Implementation

## Objective
Implement the `MCPServer` class that manages MCP protocol lifecycle, maintains the event queue, and coordinates server startup/shutdown.

## Acceptance Criteria
- [ ] `MCPServer` class exists in `src/hamlet/mcp_server/server.py`
- [ ] `async start()` method initializes MCP server and begins listening for connections
- [ ] `async stop()` method gracefully shuts down the server
- [ ] `get_event_queue()` returns the `asyncio.Queue` instance
- [ ] Server runs on stdio transport using `mcp.server.stdio.stdio_server`
- [ ] Server name is registered as "hamlet"
- [ ] Module imports successfully with no missing dependencies

## File Scope
- `src/hamlet/mcp_server/__init__.py` (create)
- `src/hamlet/mcp_server/server.py` (create)

## Dependencies
- Depends on: none
- Blocks: 002, 003, 004

## Implementation Notes

### Class Structure
```python
class MCPServer:
    def __init__(self):
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._server: Server | None = None
        self._running: bool = False

    async def start(self) -> None:
        # Initialize mcp.server.Server("hamlet")
        # Set up stdio_server context
        # Mark as running

    async def stop(self) -> None:
        # Graceful shutdown
        # Mark as not running

    def get_event_queue(self) -> asyncio.Queue:
        return self._event_queue
```

### MCP SDK Usage
Use the `mcp` Python package. The server should use `stdio_server` context manager for transport. The `Server` class from `mcp.server` handles protocol negotiation.

### Async Context
The server must properly handle the async context for stdio transport. The pattern should follow:
```python
async with stdio_server() as (read_stream, write_stream):
    await self._server.run(read_stream, write_stream, InitializationOptions())
```

### Queue Ownership
The event queue is owned by `MCPServer` and passed to handlers. Handlers push validated events to this queue. The queue is unbounded (no maxsize) to prevent blocking.

### Thread Safety
Since this runs in an asyncio event loop, use `asyncio.Queue` (not `queue.Queue`). All operations are async-safe by default in the async context.

### Error Handling
The `start()` method should catch and log exceptions from MCP SDK initialization but not re-raise them. Per guiding principle 7 (graceful degradation), server startup failures should be logged but not crash the application. However, if the server cannot start, the application should still be able to run (TUI works, simulation works, just no events received).

### Logging
Use Python's `logging` module with logger name `hamlet.mcp_server`. Log at INFO level when server starts/stops. Log at ERROR level if server fails to start.

## Complexity
Medium
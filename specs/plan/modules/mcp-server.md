# Module: MCP Server

## Scope

This module owns the Model Context Protocol (MCP) server implementation. It is responsible for:

- Receiving JSON-RPC messages from Claude Code hook scripts
- Validating incoming event payloads
- Pushing validated events to the async event queue
- Handling MCP protocol lifecycle (initialization, capabilities negotiation)

This module is NOT responsible for:

- Processing or interpreting event contents (Event Processing module)
- Inferring agent state (Agent Inference module)
- Storing events (World State module)

## Provides

- `MCPServer` class — Main MCP server instance
  - `async start()` — Start listening for connections
  - `async stop()` — Graceful shutdown
  - `get_event_queue() -> asyncio.Queue` — Returns the queue for event consumption

- `EventHandler` protocol — Interface for event handling
  - `async handle_event(event: RawEvent) -> None`

- MCP tool/resource definitions (if exposing to Claude Code):
  - Tool: `hamlet_status` — Returns current server status
  - Resource: `hamlet://world` — Returns current world state summary

## Requires

- `asyncio.Queue` (standard library) — Queue for passing events to Event Processing
- `mcp` package (Python MCP SDK) — MCP protocol implementation
- `RawEvent` type (from Event Processing module) — Event structure contract

## Boundary Rules

1. **No blocking operations.** The MCP server must not block on I/O or computation. All event handling must push to queue and return immediately.

2. **No business logic.** The server validates payload structure only. It does not interpret tool names, agent types, or world state.

3. **Fire-and-forget.** Events are pushed to queue; no response is sent back to hook scripts except acknowledgment.

4. **Thread safety.** The server runs in asyncio event loop; all queue operations must use async queue methods.

5. **Protocol compliance.** Must follow MCP specification for initialization, capabilities, and notification handling.

## Internal Design Notes

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP SERVER                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐     ┌──────────────────────────────┐   │
│  │ stdio_server  │────►│     Server (MCP Server)       │   │
│  │ (transport)   │     │                              │   │
│  └───────────────┘     │  ┌────────────────────────┐  │   │
│                        │  │ list_tools handler     │  │   │
│                        │  └────────────────────────┘  │   │
│                        │  ┌────────────────────────┐  │   │
│                        │  │ call_tool handler      │  │   │
│                        │  └────────────────────────┘  │   │
│                        │  ┌────────────────────────┐  │   │
│                        │  │ notification handler   │  │   │
│                        │  │   - hamlet/event       │  │   │
│                        │  └───────────┬────────────┘  │   │
│                        └──────────────┼───────────────┘   │
│                                       │                    │
│                                       ▼                    │
│                           ┌─────────────────────┐          │
│                           │   Event Validator   │          │
│                           │   - Schema check    │          │
│                           │   - Required fields │          │
│                           └──────────┬──────────┘          │
│                                      │                     │
│                                      ▼                     │
│                           ┌─────────────────────┐          │
│                           │   Event Queue       │          │
│                           │   (asyncio.Queue)   │          │
│                           └──────────┬──────────┘          │
│                                      │                     │
│                                      ▼                     │
│                           To Event Processing Module        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Event Validation Schema

```python
EVENT_SCHEMA = {
    "type": "object",
    "required": ["jsonrpc", "method", "params"],
    "properties": {
        "jsonrpc": {"const": "2.0"},
        "method": {"const": "hamlet/event"},
        "params": {
            "type": "object",
            "required": ["session_id", "timestamp", "hook_type", "project_id"],
            "properties": {
                "session_id": {"type": "string"},
                "timestamp": {"type": "string", "format": "iso8601"},
                "hook_type": {"enum": ["PreToolUse", "PostToolUse", "Notification", "Stop"]},
                "project_id": {"type": "string"},
                "project_name": {"type": "string"},
                "data": {"type": "object"}
            }
        }
    }
}
```

### Implementation Approach

1. Use `mcp.server.Server` from Python MCP SDK
2. Register handler for `notifications/message` method
3. Validate against schema using `jsonschema` library
4. On validation failure: log warning, discard event (no error response per guiding principle 7)
5. On validation success: create `RawEvent` object, push to queue

### Error Handling

Per guiding principle 7 (Graceful Degradation):

- Malformed JSON: Log at DEBUG level, discard
- Missing required fields: Log at WARN level, discard
- Unknown hook_type: Log at WARN level, discard
- Queue full: Log at ERROR level, discard (should never happen with proper sizing)

No exceptions should propagate to MCP protocol layer.

### Concurrency

The server runs as an async task alongside TUI and simulation:

```python
async def run_server(event_queue: asyncio.Queue):
    server = Server("hamlet")
    
    @server.list_tools()
    async def list_tools():
        return [Tool(name="hamlet_status", description="Get server status")]
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
```

The main application spawns this as a task:

```python
# In main.py
event_queue = asyncio.Queue()
server_task = asyncio.create_task(run_server(event_queue))
# ... other tasks ...
await asyncio.gather(server_task, tui_task, simulation_task)
```

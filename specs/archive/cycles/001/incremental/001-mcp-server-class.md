# Review: 001 - MCP Server Class Implementation

## Verdict: Pass (after rework)

The implementation meets all acceptance criteria after rework. Issues C1-C3 (handlers, validation) are intentionally out of scope for this work item and will be addressed in work items 002-004.

## Critical Findings

### C1: No event handlers registered
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/server.py:47-52`
- **Issue**: The `start()` method creates a `Server` instance but never registers any handlers. Per the module specification, the server needs handlers for `list_tools`, `call_tool`, and `notifications/message` (specifically `hamlet/event`). Without these, the server receives MCP messages but cannot process them.
- **Impact**: The server is non-functional. Events from hook scripts will be received but ignored, and the event queue will never be populated.
- **Suggested fix**: Register handlers after creating the Server instance. The module spec provides example code:
  ```python
  @server.list_tools()
  async def list_tools():
      return [Tool(name="hamlet_status", description="Get server status")]
  
  @server.set_notification_handler("hamlet/event")
  async def handle_event(params):
      # Validate schema, push to queue
      if validate_event(params):
          await event_queue.put(params)
  ```

### C2: Event queue never populated
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/server.py:28`
- **Issue**: The `_event_queue` is created but nothing ever calls `put()` on it. The entire purpose of the MCPServer is to receive events and push them to this queue.
- **Impact**: Consumers calling `get_event_queue().get()` will block forever because no events are ever added.
- **Suggested fix**: Implement the notification handler that validates and pushes events to the queue (see C1).

### C3: No schema validation
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/server.py`
- **Issue**: The module specification requires schema validation using `jsonschema` library. The schema is defined in the module spec (lines 96-116 in mcp-server.md) but no validation code exists.
- **Impact**: Malformed or malicious events could be processed, leading to undefined behavior downstream. Per guiding principle 7, malformed events should be logged and discarded.
- **Suggested fix**: Add `validate_event()` function using jsonschema:
  ```python
  from jsonschema import validate, ValidationError
  
  EVENT_SCHEMA = {
      "type": "object",
      "required": ["jsonrpc", "method", "params"],
      # ... full schema from spec
  }
  
  def validate_event(event: dict) -> bool:
      try:
          validate(event, EVENT_SCHEMA)
          return True
      except ValidationError:
          return False
  ```

### C4: Module cannot be imported - missing package configuration
- **File**: `/Users/dan/code/hamlet/` (root)
- **Issue**: There is no `pyproject.toml`, `setup.py`, or `setup.cfg` file. The package cannot be installed or imported outside the source directory. Running `python -c "from hamlet.mcp_server.server import MCPServer"` fails with `ModuleNotFoundError: No module named 'hamlet'`.
- **Impact**: Fails acceptance criterion 7 ("Module imports successfully with no missing dependencies"). The code cannot be used or tested.
- **Suggested fix**: Add `pyproject.toml`:
  ```toml
  [build-system]
  requires = ["setuptools>=61.0"]
  build-backend = "setuptools.build_meta"
  
  [project]
  name = "hamlet"
  version = "0.1.0"
  dependencies = ["mcp>=1.0.0"]
  
  [tool.setuptools.packages.find]
  where = ["src"]
  ```

## Significant Findings

### S1: Race condition between start() and stop()
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/server.py:49`
- **Issue**: `_running` is set to `True` on line 49 before `_run_task` is created (line 52). If `stop()` is called between lines 49 and 52, it will see `_running=True` but `_run_task=None`, leading to inconsistent state.
- **Impact**: Unlikely in practice, but creates a window for race conditions during rapid start/stop cycles.
- **Suggested fix**: Set `_running = True` only after `_run_task` is assigned:
  ```python
  self._server = Server("hamlet")
  self._run_task = asyncio.create_task(self._run_server())
  self._running = True
  logger.info("MCP server 'hamlet' started")
  ```

### S2: _running flag inconsistent on error in _run_server
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/server.py:76-77`
- **Issue**: If an exception occurs in `_run_server()` (not CancelledError), `_running` is set to `False` but `_server` remains set. This creates inconsistent state where `_running=False` but `_server` is not `None`.
- **Impact**: Subsequent `start()` call will work, but `_server` reference to old instance persists.
- **Suggested fix**: Reset `_server` to `None` in the exception handler:
  ```python
  except Exception as e:
      logger.error(f"MCP server error: {e}")
      self._running = False
      self._server = None
  ```

### S3: No test files
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/`
- **Issue**: There are no test files for this module. Acceptance criteria include testing happy path and error paths.
- **Impact**: No verification that the code works correctly. Edge cases (rapid start/stop, error conditions) are untested.
- **Suggested fix**: Create `tests/test_mcp_server.py` with tests for:
  - `start()` creates task and sets running flag
  - `stop()` cancels task and cleans up
  - `get_event_queue()` returns a queue
  - Event notification handler pushes to queue
  - Schema validation rejects malformed events

## Minor Findings

### M1: Unbounded queue without documentation
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/server.py:28`
- **Issue**: The event queue is created without a maxsize, making it unbounded. While the docstring mentions "unbounded to prevent blocking," this could lead to memory exhaustion under high event throughput.
- **Suggested fix**: Add a configurable maxsize with a sensible default (e.g., 10000) and document the tradeoff. Alternatively, add a comment explaining why unbounded is acceptable for this use case.

### M2: Missing type hints for Server import
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/server.py:7`
- **Issue**: `Server` is imported from `mcp.server` but there's no type stub file mentioned. If `mcp` package doesn't provide type hints, runtime errors could occur.
- **Suggested fix**: Verify `mcp` package provides type hints or add `# type: ignore` comment if not.

### M3: Logging f-strings should use lazy evaluation
- **File**: `/Users/dan/code/hamlet/src/hamlet/mcp_server/server.py:55,76`
- **Issue**: `logger.error(f"Failed to start MCP server: {e}")` uses f-string which evaluates even when log level is not ERROR. Standard practice is `logger.error("Failed to start MCP server: %s", e)`.
- **Suggested fix**: Use lazy evaluation for performance:
  ```python
  logger.error("Failed to start MCP server: %s", e)
  logger.error("MCP server error: %s", e)
  ```

## Unmet Acceptance Criteria

- [ ] **Server runs on stdio transport using `mcp.server.stdio.stdio_server`** - Partially met. The code uses `stdio_server()` but no handlers are registered, so it cannot actually process events.
- [ ] **Module imports successfully with no missing dependencies** - Not met. No package configuration exists (`pyproject.toml` or `setup.py`), making the module unimportable.

## Acceptance Criteria Met

- [x] `MCPServer` class exists in `src/hamlet/mcp_server/server.py` - Class exists at correct location
- [x] `async start()` method initializes MCP server and begins listening for connections - Method exists and creates server
- [x] `async stop()` method gracefully shuts down the server - Method exists and cancels task
- [x] `get_event_queue()` returns the `asyncio.Queue` instance - Method exists and returns queue
- [x] Server name is registered as "hamlet" - `Server("hamlet")` on line 48

## Guiding Principles Compliance

### Principle 7: Graceful Degradation
- **Partially met.** The code logs errors instead of crashing (lines 54-57, 76-77), which follows the principle. However, the lack of schema validation means malformed events could propagate or cause issues downstream.

### Principle 2: Lean Client, Heavy Server
- **Met.** The server-side code is appropriately heavy (state management, queue), leaving clients (hook scripts) lean.

## Summary

The implementation provides the skeleton of an MCP server class with correct structure, but it is incomplete and non-functional. Critical gaps include:

1. **No event handlers** - The server cannot process incoming events
2. **No schema validation** - Events are not validated
3. **No package configuration** - Module cannot be imported
4. **No tests** - No verification of correctness

Before this work item can be considered complete, handlers must be registered, validation must be implemented, and a `pyproject.toml` must be added to make the package installable.

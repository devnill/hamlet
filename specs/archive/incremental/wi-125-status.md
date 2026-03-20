# WI-125 Status Report — Add REST state endpoints to MCP server

## What was implemented

- Created `/Users/dan/code/hamlet/src/hamlet/mcp_server/serializers.py` with:
  - `serialize_state(world_state, animation_manager=None) -> dict` (async) — calls `get_all_agents()`, `get_all_structures()`, `get_all_villages()`, `get_projects()`, serializes each into JSON-safe dicts
  - `serialize_events(world_state) -> dict` (async) — calls `get_event_log()`, serializes events
  - Private helpers `_serialize_agent`, `_serialize_structure`, `_serialize_village`, `_serialize_project`, `_serialize_event`

- Modified `/Users/dan/code/hamlet/src/hamlet/mcp_server/server.py`:
  - Added `from .serializers import serialize_events, serialize_state` import
  - Added `animation_manager: Any = None` parameter to `MCPServer.__init__`, stored as `self._animation_manager`
  - Registered two new routes in `start()`: `GET /hamlet/state` and `GET /hamlet/events`
  - Added `_handle_state` and `_handle_events` handler methods with exception handling returning `{"error": ...}` at status 500

## Deviations from spec

- `serialize_state` and `serialize_events` are `async` functions (not plain functions as implied by the spec). This is required because the `WorldStateManager` methods they call (`get_all_agents()`, etc.) are all `async` coroutines that acquire an asyncio lock internally. Making them sync would require `asyncio.run()` inside an already-running event loop, which would fail.

- For `animation_frames`, the spec says "call its method to get frames" when `animation_manager` is provided, but `AnimationManager` has no dedicated method returning the frames dict — it only has `_frames` as a private attribute. The implementation reads `animation_manager._frames` directly (as a copy via `dict(...)`), which is consistent with how the rest of the codebase accesses animation state.

## Files modified/created

- **Created**: `src/hamlet/mcp_server/serializers.py`
- **Modified**: `src/hamlet/mcp_server/server.py`

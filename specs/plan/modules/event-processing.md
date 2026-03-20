# Module: Event Processing

## Scope

This module owns the transformation of raw hook events into normalized internal events. It is responsible for:

- Consuming raw events from the MCP server queue
- Normalizing event format and structure
- Adding sequence numbers and processing timestamps
- Enriching events with derived data (project context, session context)
- Routing normalized events to Agent Inference and World State modules

This module is NOT responsible for:

- Receiving events from network (MCP Server module)
- Inferring agent lifecycle (Agent Inference module)
- Storing or displaying events (World State module)

## Provides

- `EventProcessor` class — Main event processing pipeline
  - `async start()` — Begin consuming from queue
  - `async stop()` — Graceful shutdown
  - `async process_event(raw: RawEvent) -> InternalEvent` — Transform single event

- `InternalEvent` dataclass — Normalized event structure
  - `id: str` — UUID
  - `sequence: int` — Monotonic sequence number
  - `received_at: datetime`
  - `session_id: str`
  - `project_id: str`
  - `project_name: str`
  - `hook_type: HookType`
  - `tool_name: str | None`
  - `tool_input: dict | None`
  - `tool_output: dict | None`
  - `success: bool | None`
  - `duration_ms: int | None`
  - `raw_payload: dict` — Original payload for debugging

- `EventRouter` interface — Routes events to subscribers
  - `subscribe(callback: EventCallback)` — Register event consumer
  - `unsubscribe(callback: EventCallback)` — Remove event consumer

## Requires

- `asyncio.Queue` (standard library) — Input queue from MCP Server
- `RawEvent` (from MCP Server module) — Input event format
- `WorldState.update_session(session_id, project_id)` — Update session tracking
- `AgentInference.process_event(event)` — Infer agent state from events
- `Persistence.write_event(event)` — Persist event to log

## Boundary Rules

1. **No network I/O.** This module processes events in memory only. Network operations are in MCP Server.

2. **No state mutation except routing.** Events are transformed and routed; world state changes happen in World State module.

3. **Deterministic transformation.** Same raw event always produces same internal event. No randomness.

4. **Ordering guarantee.** Events are processed in order received. Sequence numbers are monotonic.

5. **Fail-fast on corruption.** If an event cannot be normalized, log error and discard. Do not crash the pipeline.

## Internal Design Notes

### Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    EVENT PROCESSOR                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Raw Event (from MCP Server queue)                          │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 NORMALIZE                            │   │
│  │  - Parse timestamp                                   │   │
│  │  - Assign UUID                                      │   │
│  │  - Assign sequence number                           │   │
│  │  - Extract tool fields (if applicable)              │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                    │
│                        ▼                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 ENRICH                                │   │
│  │  - Add project context (from World State)            │   │
│  │  - Add session context (from World State)            │   │
│  │  - Resolve project_id to village_id                 │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                    │
│                        ▼                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 VALIDATE                              │   │
│  │  - Check required fields                             │   │
│  │  - Verify project exists                             │   │
│  │  - Verify hook_type is valid                         │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                    │
│                        ▼                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 ROUTE                                 │   │
│  │  - Send to Agent Inference (for PreToolUse/PostTool) │   │
│  │  - Send to World State (for all events)              │   │
│  │  - Send to Persistence (for logging)                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Event Type Routing

| Hook Type | Agent Inference | World State | Persistence |
|-----------|-----------------|-------------|-------------|
| PreToolUse | Yes (detect activity) | Yes (update session) | Yes |
| PostToolUse | Yes (pair with PreToolUse) | Yes (add work units) | Yes |
| Notification | No | Yes (log event) | Yes |
| Stop | Yes (detect completion) | Yes (session end) | Yes |

### Sequence Number Generation

```python
class SequenceGenerator:
    """Thread-safe monotonic sequence generator."""
    
    def __init__(self):
        self._counter = 0
        self._lock = asyncio.Lock()
    
    async def next(self) -> int:
        async with self._lock:
            self._counter += 1
            return self._counter
```

Sequence numbers are per-process and not persisted. On restart, they reset to 1.

### Implementation Approach

```python
class EventProcessor:
    def __init__(self, event_queue: asyncio.Queue, world_state: WorldState, 
                 agent_inference: AgentInference, persistence: Persistence):
        self._queue = event_queue
        self._world_state = world_state
        self._agent_inference = agent_inference
        self._persistence = persistence
        self._sequence = SequenceGenerator()
        self._running = False
    
    async def start(self):
        self._running = True
        while self._running:
            try:
                raw_event = await self._queue.get()
                internal_event = await self._process(raw_event)
                await self._route(internal_event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log and continue (guiding principle 7)
                logger.error(f"Event processing error: {e}")
    
    async def _process(self, raw: RawEvent) -> InternalEvent:
        seq = await self._sequence.next()
        return InternalEvent(
            id=str(uuid4()),
            sequence=seq,
            received_at=datetime.utcnow(),
            session_id=raw.params["session_id"],
            project_id=raw.params["project_id"],
            project_name=raw.params.get("project_name", "Unknown"),
            hook_type=raw.params["hook_type"],
            tool_name=raw.params.get("data", {}).get("tool_name"),
            tool_input=raw.params.get("data", {}).get("tool_input"),
            tool_output=raw.params.get("data", {}).get("tool_output"),
            success=raw.params.get("data", {}).get("success"),
            duration_ms=raw.params.get("data", {}).get("duration_ms"),
            raw_payload=raw.params
        )
    
    async def _route(self, event: InternalEvent):
        # Update session tracking
        await self._world_state.update_session(
            event.session_id, 
            event.project_id
        )
        
        # Send to Agent Inference
        if event.hook_type in ("PreToolUse", "PostToolUse", "Stop"):
            await self._agent_inference.process_event(event)
        
        # Log event
        await self._persistence.write_event(event)
```

### Error Handling

- Invalid timestamp format: Use current time as fallback
- Missing tool_name for tool hooks: Set to None (agent inference handles it)
- Unknown project_id: Create new project in World State
- All errors logged but do not interrupt processing

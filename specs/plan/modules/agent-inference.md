# Module: Agent Inference

## Scope

This module owns the inference of agent lifecycle and type from tool usage patterns. It is responsible for:

- Detecting agent spawning (inferred from concurrent tool usage)
- Detecting agent completion (inferred from PostToolUse patterns)
- Tracking parent-child relationships between agents
- Inferring agent type from tool frequency patterns
- Detecting idle/zombie state from last-seen timestamps
- Maintaining inference state (pending PreToolUse events, session tracking)

This module is NOT responsible for:

- Receiving events (Event Processing module)
- Storing agent state (World State module)
- Rendering agents (TUI module)

## Provides

- `AgentInferenceEngine` class — Main inference engine
  - `async process_event(event: InternalEvent)` — Process an event
  - `get_inference_state() -> InferenceState` — Current inference state (for debugging)

- `InferenceResult` dataclass — Result of inference
  - `action: "spawn" | "update" | "complete" | "idle"`
  - `agent_id: str | None`
  - `parent_id: str | None`
  - `inferred_type: AgentType | None`
  - `position: Position | None`

- `AgentType` enum — Inferred agent types
  - `RESEARCHER` — High Read/Grep/Glob frequency
  - `CODER` — High Write/Edit frequency
  - `EXECUTOR` — High Bash frequency
  - `ARCHITECT` — Mixed tool usage, planning patterns
  - `TESTER` — Test-related tool patterns
  - `GENERAL` — Default/fallback type

## Requires

- `InternalEvent` (from Event Processing module) — Input events
- `WorldState` (from World State module) — Query and update agents
  - `get_or_create_agent(session_id, parent_id) -> Agent`
  - `update_agent(agent_id, fields)`
  - `get_agents_by_session(session_id) -> List[Agent]`
- `AgentType.color` property — Deterministic color mapping

## Boundary Rules

1. **No persistent state.** Inference state (pending events, pattern windows) is in-memory only. World State owns persistent agent data.

2. **Probabilistic, not certain.** Inference is best-effort. False positives/negatives are acceptable per guiding principle 7.

3. **Deterministic color.** Agent color is derived deterministically from agent type, not randomly assigned.

4. **Session-scoped.** Agent identity is tied to session_id. Cross-session agent tracking is not supported.

5. **No blocking on World State.** All World State calls must be async and non-blocking.

## Internal Design Notes

### Inference State

```python
@dataclass
class InferenceState:
    # Pending PreToolUse events (waiting for PostToolUse)
    pending_tools: Dict[str, PendingTool]  # key: tool_call_id
    
    # Session tracking
    sessions: Dict[str, SessionState]  # key: session_id
    
    # Tool frequency windows (for type inference)
    tool_windows: Dict[str, ToolWindow]  # key: session_id
    
    # Last seen timestamps
    last_seen: Dict[str, datetime]  # key: agent_id

@dataclass
class PendingTool:
    session_id: str
    tool_name: str
    tool_input: dict
    started_at: datetime
    estimated_agent_id: str  # Agent we think owns this tool call

@dataclass  
class SessionState:
    session_id: str
    project_id: str
    known_agents: List[str]  # Agent IDs
    last_activity: datetime
    active_tools: int  # Count of pending PreToolUse events

@dataclass
class ToolWindow:
    """Sliding window of recent tool usage for type inference."""
    events: List[Tuple[str, datetime]]  # (tool_name, timestamp)
    window_size: timedelta
```

### Agent Spawn Detection

The key challenge: Claude Code doesn't expose agent spawning events. We must infer.

**Detection Heuristics:**

1. **Concurrent Tool Usage:**
   - If a session has multiple overlapping tool calls (PreToolUse without matching PostToolUse)
   - AND the concurrent calls are for different agent instances
   - THEN infer a spawn

2. **New Session ID:**
   - If a session_id appears that wasn't in the project's session list
   - AND it has a parent-child relationship inferred from context
   - THEN create a new agent for that session

3. **Parent-Child Proximity:**
   - New agents spawn near their parent agent's position
   - Parent is inferred from the agent that was active when spawn was detected

```python
async def _detect_spawn(self, event: InternalEvent, state: InferenceState) -> Optional[InferenceResult]:
    """
    Detect if this event indicates a new agent spawned.
    
    Heuristics:
    1. PreToolUse while another tool is pending (concurrent activity)
    2. Different session_id than existing session's agents
    3. Nested tool call patterns
    """
    session = state.sessions.get(event.session_id)
    
    if not session:
        # New session - first agent for this session
        return InferenceResult(
            action="spawn",
            agent_id=str(uuid4()),
            parent_id=None,  # No parent for session-first agent
            inferred_type=AgentType.GENERAL,
            position=None  # Will be assigned by World State
        )
    
    # Check for concurrent activity (potential spawn)
    if session.active_tools > 0 and event.hook_type == "PreToolUse":
        # There's already a pending tool in this session
        # This might be a spawned agent
        # Create new agent near parent
        parent_agent = await self._world_state.get_primary_agent(event.session_id)
        return InferenceResult(
            action="spawn",
            agent_id=str(uuid4()),
            parent_id=parent_agent.id if parent_agent else None,
            inferred_type=AgentType.GENERAL,
            position=None  # Will be calculated by World State near parent
        )
    
    return None
```

### Agent Type Inference

Type is inferred from tool usage patterns over a sliding window:

```python
TYPE_RULES = [
    # (tool_patterns, minimum_ratio, inferred_type)
    (["Read", "Grep", "Glob"], 0.6, AgentType.RESEARCHER),
    (["Write", "Edit"], 0.6, AgentType.CODER),
    (["Bash"], 0.5, AgentType.EXECUTOR),
    (["Task"], 0.4, AgentType.ARCHITECT),
]

async def _infer_type(self, session_id: str, state: InferenceState) -> AgentType:
    """
    Infer agent type from recent tool usage.
    
    Uses sliding window of recent events (default: 100 events or 5 minutes).
    """
    window = state.tool_windows.get(session_id)
    if not window or len(window.events) < 10:
        return AgentType.GENERAL  # Not enough data
    
    # Count tool frequencies
    tool_counts = Counter(tool for tool, _ in window.events)
    total = len(window.events)
    
    # Check each rule
    for patterns, min_ratio, agent_type in TYPE_RULES:
        match_count = sum(tool_counts.get(p, 0) for p in patterns)
        if match_count / total >= min_ratio:
            return agent_type
    
    return AgentType.GENERAL
```

### Idle/Zombie Detection

```python
ZOMBIE_THRESHOLD = timedelta(minutes=5)  # Configurable

async def _check_zombie(self, agent_id: str, state: InferenceState) -> bool:
    """
    Check if agent has become a zombie (idle for too long).
    
    Zombie state is transient - agents can become active again.
    """
    last_seen = state.last_seen.get(agent_id)
    if not last_seen:
        return False
    
    return datetime.utcnow() - last_seen > ZOMBIE_THRESHOLD
```

### Color Assignment

Colors are deterministic based on agent type:

```python
TYPE_COLORS = {
    AgentType.RESEARCHER: "cyan",     # Research = knowledge = cyan/water
    AgentType.CODER: "yellow",        # Coding = construction = yellow
    AgentType.EXECUTOR: "green",      # Execution = action = green
    AgentType.ARCHITECT: "magenta",   # Planning = special = magenta
    AgentType.TESTER: "blue",         # Testing = verification = blue
    AgentType.GENERAL: "white",       # Default = neutral = white
}

def get_color(agent_type: AgentType) -> str:
    return TYPE_COLORS.get(agent_type, "white")
```

Zombie state modifies color:

```python
def get_display_color(agent: Agent) -> str:
    base_color = TYPE_COLORS.get(agent.inferred_type, "white")
    if agent.state == "zombie":
        # Zombie = greenish tint (per interview)
        # Blend base color with green
        return blend_color(base_color, "green", ratio=0.5)
    return base_color
```

### Implementation Approach

```python
class AgentInferenceEngine:
    def __init__(self, world_state: WorldState):
        self._world_state = world_state
        self._state = InferenceState()
    
    async def process_event(self, event: InternalEvent):
        # Update last seen
        self._state.last_seen[event.session_id] = event.received_at
        
        # Update tool window for type inference
        if event.tool_name:
            self._update_tool_window(event)
        
        # Process based on hook type
        if event.hook_type == "PreToolUse":
            await self._handle_pre_tool_use(event)
        elif event.hook_type == "PostToolUse":
            await self._handle_post_tool_use(event)
        elif event.hook_type == "Stop":
            await self._handle_stop(event)
    
    async def _handle_pre_tool_use(self, event: InternalEvent):
        # Check for spawn
        spawn_result = await self._detect_spawn(event, self._state)
        if spawn_result:
            agent = await self._world_state.create_agent(
                session_id=event.session_id,
                parent_id=spawn_result.parent_id,
                inferred_type=spawn_result.inferred_type
            )
            spawn_result.agent_id = agent.id
        
        # Record pending tool
        self._state.pending_tools[event.sequence] = PendingTool(
            session_id=event.session_id,
            tool_name=event.tool_name,
            tool_input=event.tool_input or {},
            started_at=event.received_at,
            estimated_agent_id=spawn_result.agent_id if spawn_result else None
        )
        
        # Update session active count
        session = self._state.sessions.setdefault(event.session_id, SessionState())
        session.active_tools += 1
    
    async def _handle_post_tool_use(self, event: InternalEvent):
        # Find matching PreToolUse
        pending = self._state.pending_tools.pop(event.sequence, None)
        if not pending:
            return  # Orphan PostToolUse, ignore
        
        # Update session active count
        session = self._state.sessions.get(event.session_id)
        if session:
            session.active_tools -= 1
        
        # Calculate work units (for construction progress)
        duration_ms = event.duration_ms or 0
        work_units = duration_ms / 100  # Scale: 100ms = 1 work unit
        
        # Update agent
        agent_id = pending.estimated_agent_id or await self._get_primary_agent(event.session_id)
        if agent_id:
            await self._world_state.update_agent(agent_id, {
                "last_seen": event.received_at,
                "state": "active",
                "total_work_units": +work_units  # Atomic increment
            })
            
            # Re-infer type periodically
            inferred_type = await self._infer_type(event.session_id, self._state)
            await self._world_state.update_agent(agent_id, {
                "inferred_type": inferred_type
            })
```

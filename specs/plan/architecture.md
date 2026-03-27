# Architecture: Hamlet

## System Overview

Hamlet is a terminal-based idle game that visualizes Claude Code agent activity as ASCII characters building a village. It doubles as an observability platform for multi-agent orchestration. The system receives hook events from multiple Claude Code sessions via the Model Context Protocol (MCP), processes them to infer agent lifecycle and activity, and renders a persistent world where agents (`@` symbols) construct structures that evolve over time.

### Component Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HAMLET SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐                                                           │
│  │ Claude Code  │  (Multiple sessions, external)                           │
│  │   Session    │                                                           │
│  │    Hooks     │                                                           │
│  └──────┬───────┘                                                           │
│         │ JSON via stdin/stdout                                             │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         HOOK SCRIPTS                                 │   │
│  │  PreToolUse, PostToolUse, Notification, Stop                         │   │
│  │  (Minimal processing: extract agent/tool info, send to MCP)          │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ JSON-RPC over stdio/SSE                   │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      MCP SERVER MODULE                               │   │
│  │  - Receives events from all sessions                                 │   │
│  │  - Validates payload structure                                       │   │
│  │  - Pushes to async event queue                                        │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ asyncio.Queue                             │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    EVENT PROCESSING MODULE                           │   │
│  │  - Normalizes event format                                           │   │
│  │  - Enriches with timestamp, sequence ID                              │   │
│  │  - Routes to Agent Inference or World State                           │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│         ┌───────────────────────┴───────────────────────┐                  │
│         ▼                                               ▼                  │
│  ┌────────────────────────┐              ┌────────────────────────┐        │
│  │  AGENT INFERENCE       │              │     WORLD STATE        │        │
│  │  MODULE                │◄────────────►│     MODULE              │        │
│  │  - Detects agent       │   queries/   │  - Projects            │        │
│  │    spawning from       │   updates    │  - Villages (per       │        │
│  │    tool patterns       │              │    project)           │        │
│  │  - Tracks parent-      │              │  - Agents              │        │
│  │    child relationships │              │  - Structures          │        │
│  │  - Infers agent type   │              │  - World grid          │        │
│  │  - Detects idle/zombie │              │  - Session registry    │        │
│  │    state               │              │                        │        │
│  └────────────────────────┘              └───────────┬────────────┘        │
│                                                      │                      │
│                                                      ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SIMULATION MODULE                               │   │
│  │  - Game loop (independent of event arrival)                          │   │
│  │  - Construction progress tick                                        │   │
│  │  - Structure evolution (wood -> stone)                               │   │
│  │  - Animation state management                                        │   │
│  │  - Road building between villages                                    │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      VIEWPORT MODULE                                 │   │
│  │  - Coordinate system (world coordinates)                             │   │
│  │  - Viewport position and size                                        │   │
│  │  - Scroll handling                                                   │   │
│  │  - World-to-screen coordinate translation                            │   │
│  │  - Agent visibility tracking                                         │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        TUI MODULE                                    │   │
│  │  - Textual application                                               │   │
│  │  - World view (main area)                                            │   │
│  │  - Status line (agents, structures, project)                        │   │
│  │  - Event log (bottom, scrollable)                                    │   │
│  │  - Legend/menu overlay                                               │   │
│  │  - Input handling (scroll, menu navigation)                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        GUI MODULE                                    │   │
│  │  gui/renderer_protocol.py — RendererProtocol (render_frame+cleanup) │   │
│  │  gui/symbol_config.py — SymbolConfig, AgentVisual, etc.            │   │
│  │  gui/detect.py — detect_renderer(), resolve_renderer()              │   │
│  │  gui/kitty/                                                         │   │
│  │    protocol.py — Kitty APC escape sequences (upload/display/delete) │   │
│  │    renderer.py — KittyRenderer (implements RendererProtocol)        │   │
│  │    sprites.py — SpriteManager, SpriteHandle (PNG loading+caching)   │   │
│  │    app.py — KittyApp (30fps render loop, input, legend)            │   │
│  │    state_fetcher.py — HTTP state polling (urllib, no subprocess)    │   │
│  │    zoom.py — ZoomLevel, ZoomConfig (CLOSE/MEDIUM/FAR)              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     PERSISTENCE MODULE                               │   │
│  │  - SQLite database                                                   │   │
│  │  - Schema: projects, villages, agents, structures, events          │   │
│  │  - Read/write operations                                              │   │
│  │  - Transaction handling                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Event Flow: Hook to World State

```
1. Claude Code triggers hook (PreToolUse/PostToolUse/Notification/Stop)
   │
2. Hook script reads JSON from stdin
   │
3. Hook script extracts:
   - session_id (from env or payload)
   - timestamp
   - hook_type
   - tool_name (for PreToolUse/PostToolUse)
   - tool_input (simplified, minimal)
   - tool_output (for PostToolUse, success/failure only)
   - project_id (from config file in working directory)
   │
4. Hook script sends via MCP to Hamlet server
   - Uses JSON-RPC notification
   - Fire-and-forget (no retry on failure)
   │
5. MCP Server receives and validates:
   - Required fields present
   - Valid hook type
   - Pushes to async event queue
   │
6. Event Processing normalizes:
   - Adds sequence number
   - Parses timestamp
   - Creates internal event object
   │
7. Agent Inference analyzes:
   - Correlates PreToolUse/PostToolUse pairs
   - Detects concurrent tool usage (agent spawning)
   - Infers agent type from tool patterns
   - Updates agent last-seen timestamp
   │
8. World State updates:
   - Creates/updates agents
   - Records tool activity for work tracking
   - Updates structure progress (if applicable)
   │
9. Simulation loop (independent):
   - Processes work queue
   - Advances construction progress
   - Triggers structure evolution
   - Updates agent animation states
   │
10. Viewport translates:
    - World coordinates to screen coordinates
    - Determines visible agents/structures
    │
11. TUI renders:
    - Renders visible world slice
    - Updates status line
    - Appends to event log
```

### World Simulation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   SIMULATION TICK (per frame)                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  For each agent:                                             │
│    - Update last-seen delta                                  │
│    - If delta > ZOMBIE_THRESHOLD: mark as zombie            │
│    - Update animation frame (spin: - \ | /)                  │
│                                                              │
│  For each structure:                                         │
│    - Accumulate work units from recent tool activity         │
│    - If work >= threshold: increment construction stage     │
│    - If stage complete: trigger evolution (wood -> stone)   │
│                                                              │
│  For world:                                                  │
│    - Check village expansion conditions                      │
│    - Build roads between nearby villages                     │
│    - Clean up stale session references                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Module Specifications

See `/Users/dan/code/hamlet/specs/plan/modules/` for detailed module specifications:

1. **MCP Server Module** — Handles MCP protocol, receives hook events
2. **Event Processing Module** — Normalizes and routes events
3. **Agent Inference Module** — Detects agent lifecycle from patterns
4. **World State Module** — Core data model and state management
5. **Simulation Module** — Game loop and world progression
6. **Viewport Module** — Coordinate system and scrolling
7. **TUI Module** — Textual application and rendering
8. **Persistence Module** — SQLite storage layer

## Interface Contracts

### Contract: HookEvent (Hook Script → MCP Server)

```typescript
// Hook script sends to MCP server via HTTP POST (JSON-RPC 2.0 envelope)
// NOTE (updated 2026-03-16): event-specific fields are sent FLAT in params,
// not nested under a "data" sub-object. EventProcessor reads params directly.
// The "data" nesting shown in earlier architecture drafts does not match the
// implementation and is not the canonical format.
interface HookEvent {
  jsonrpc: "2.0";
  method: "hamlet/event";
  params: {
    session_id: string;           // UUID from Claude Code hook input (stdin)
    timestamp: string;            // ISO-8601
    hook_type: "PreToolUse" | "PostToolUse" | "Notification" | "Stop";
    project_id: string;           // From .hamlet/config.json (find_config())
    project_name: string;         // From .hamlet/config.json (find_config())
    tool_name?: string;           // For PreToolUse/PostToolUse (from stdin)
    tool_input?: object;          // For PreToolUse/PostToolUse (from stdin)
    tool_output?: object;         // For PostToolUse (from stdin tool_response)
    success?: boolean;            // For PostToolUse
    duration_ms?: number;         // For PostToolUse (computed via timing temp file)
    notification_type?: string;   // For Notification
    notification_message?: string;// For Notification (from stdin message)
    stop_reason?: string;         // For Stop
  };
}
```

### Contract: InternalEvent (MCP Server → Event Processing)

```typescript
// Normalized internal event
interface InternalEvent {
  id: string;                  // UUID
  sequence: number;            // Monotonic counter
  received_at: Date;
  session_id: string;
  project_id: string;
  project_name: string;
  hook_type: HookType;
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  tool_output: Record<string, unknown> | null;
  success: boolean | null;
  duration_ms: number | null;
  raw_payload: Record<string, unknown>;  // Original for debugging
}
```

### Contract: AgentState (World State)

```typescript
interface Agent {
  id: string;                  // UUID
  session_id: string;          // Owning session
  project_id: string;          // Project this agent belongs to
  parent_id: string | null;     // Parent agent (if spawned)
  inferred_type: AgentType;    // Inferred from tool patterns
  color: string;               // Deterministic from type
  position: { x: number; y: number };  // World coordinates
  last_seen: Date;
  state: "active" | "idle" | "zombie";
  current_activity: ActivityType | null;
  total_work_units: number;    // Cumulative contribution
}

type AgentType = "researcher" | "coder" | "planner" | "architect" | "tester" | "general";

type ActivityType = "reading" | "writing" | "editing" | "searching" | "executing" | "thinking";
```

### Contract: WorldState (World State Module)

```typescript
interface WorldState {
  projects: Map<string, Project>;
  sessions: Map<string, Session>;
  agents: Map<string, Agent>;
  villages: Map<string, Village>;  // Keyed by project_id
  structures: Map<string, Structure>;
  event_log: EventLogEntry[];      // Recent events for display
}

interface Project {
  id: string;
  name: string;
  config: ProjectConfig;
  village_id: string;
}

interface Session {
  id: string;
  project_id: string;
  started_at: Date;
  last_activity: Date;
  agent_ids: string[];
}

interface Village {
  id: string;
  project_id: string;
  name: string;
  center: { x: number; y: number };
  bounds: { min_x: number; min_y: number; max_x: number; max_y: number };
  structure_ids: string[];
  agent_ids: string[];
}

interface Structure {
  id: string;
  village_id: string;
  type: StructureType;
  position: { x: number; y: number };
  stage: number;              // 0-3 (foundation -> complete)
  material: "wood" | "stone" | "brick";
  work_units: number;         // Accumulated work toward next stage
  work_required: number;      // Threshold for stage advancement
}

type StructureType = "house" | "workshop" | "library" | "forge" | "tower" | "road" | "well";
```

### Contract: ViewportState (Viewport Module)

```typescript
interface ViewportState {
  center: { x: number; y: number };     // World coordinates at center
  size: { width: number; height: number }; // Screen cells
  follow_mode: "center" | "free";
  visible_agents: string[];              // Agent IDs in view
  visible_structures: string[];          // Structure IDs in view
}

// Coordinate translation
function worldToScreen(world_pos: Position, viewport: ViewportState): Position {
  return {
    x: world_pos.x - viewport.center.x + Math.floor(viewport.size.width / 2),
    y: world_pos.y - viewport.center.y + Math.floor(viewport.size.height / 2)
  };
}

function screenToWorld(screen_pos: Position, viewport: ViewportState): Position {
  return {
    x: screen_pos.x + viewport.center.x - Math.floor(viewport.size.width / 2),
    y: screen_pos.y + viewport.center.y - Math.floor(viewport.size.height / 2)
  };
}
```

### Contract: RenderCommand (TUI Module)

```typescript
interface RenderCommand {
  type: "cell" | "text" | "clear";
  position: { x: number; y: number };  // Screen coordinates
  char: string;                        // Single character for cell
  text: string;                         // For text type
  style: {
    color: string;
    bg_color: string | null;
    bold: boolean;
    dim: boolean;
  };
}

interface WorldRenderData {
  viewport: ViewportState;
  cells: RenderCell[];
  agents: AgentRenderData[];
  structures: StructureRenderData[];
}

interface AgentRenderData {
  screen_position: { x: number; y: number };
  symbol: "@";              // Always @ for agents
  color: string;           // Deterministic from type
  animation_frame: number; // For spin animation
  animation_type: "spin" | "idle" | "pulse" | null;
}

interface StructureRenderData {
  screen_position: { x: number; y: number };
  symbol: string;          // Depends on type and stage
  color: string;          // Depends on material
}
```

## Execution Order

### Initialization Sequence

```
1. Application Start
   │
2. Persistence Module
   │  - Load SQLite database
   │  - Read world state from disk
   │  - Initialize in-memory state
   │
3. World State Module
   │  - Restore projects, villages, agents, structures
   │  - Initialize event log
   │
4. Viewport Module
   │  - Set initial center (last viewed position or first village)
   │  - Calculate visible entities
   │
5. TUI Module
   │  - Initialize Textual app
   │  - Set up widgets (world view, status line, log)
   │
6. MCP Server Module
   │  - Start MCP server listener
   │  - Create asyncio task for event processing
   │
7. Simulation Module
   │  - Start game loop timer
   │  - Initialize tick counter
   │
8. Event Processing Module
   │  - Start event queue consumer
   │
9. Agent Inference Module
   │  - Load inference rules
   │  - Initialize pattern matchers
   │
10. Run Main Loop
    │  - TUI event loop
    │  - MCP server listener (concurrent)
    │  - Simulation ticker (concurrent)
```

### Parallel Groups

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONCURRENT TASKS                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GROUP A: Initialization (Sequential)                           │
│    Persistence → World State → Viewport → TUI setup             │
│                                                                  │
│  GROUP B: Server Startup (Sequential after A)                    │
│    MCP Server → Event Processing → Agent Inference               │
│                                                                  │
│  GROUP C: Runtime Loop (Concurrent after A & B)                  │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│    │ TUI Loop     │  │ MCP Server   │  │ Simulation       │     │
│    │ (Textual)    │  │ (stdio/SSE)  │  │ (timer-based)     │     │
│    └──────────────┘  └──────────────┘  └──────────────────┘     │
│           │                 │                    │               │
│           │                 ▼                    │               │
│           │         Event Queue                  │               │
│           │                 │                    │               │
│           │                 ▼                    │               │
│           │         Event Processing            │               │
│           │                 │                    │               │
│           │                 ▼                    │               │
│           │         World State Update          │               │
│           │                 │                    │               │
│           │                 ▼                    │               │
│           │         Viewport Update              │               │
│           │                 │                    │               │
│           ▼                 ▼                    ▼               │
│        Re-render (triggered by state change)                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Critical Path

```
Application Start
    → Persistence initialization (blocking)
    → World State restoration (blocking)
    → TUI setup (blocking)
    → MCP Server start (async task)
    → Simulation start (async task)
    → TUI run (blocking main loop)
```

The critical path is sequential through initialization. After TUI starts, all other components run as concurrent asyncio tasks.

## State Management Strategy

### State Ownership

| State | Owner | Access Pattern |
|-------|-------|----------------|
| Projects | World State Module | Read-heavy, write on new project |
| Sessions | World State Module | Write on session start/stop |
| Agents | World State Module | Frequent writes (activity updates) |
| Structures | World State Module | Frequent writes (construction progress) |
| Viewport | Viewport Module | Read-heavy, write on scroll |
| Event Log | World State Module | Append-only |
| Inference State | Agent Inference Module | Internal state, not persisted |

### Concurrency Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     ASYNCIO ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Main Thread (asyncio event loop)                               │
│  │                                                               │
│  ├── TUI Task (Textual app.run_async())                         │
│  │     - Handles rendering                                       │
│  │     - Processes user input                                    │
│  │     - Updates on reactive state changes                      │
│  │                                                               │
│  ├── MCP Server Task (stdio_server())                          │
│  │     - Listens for incoming MCP connections                    │
│  │     - Parses JSON-RPC                                         │
│  │     - Pushes events to queue                                  │
│  │                                                               │
│  ├── Event Processing Task                                       │
│  │     - Consumes from event queue                               │
│  │     - Normalizes events                                        │
│  │     - Updates World State                                     │
│  │     - Triggers Agent Inference                                │
│  │                                                               │
│  └── Simulation Task                                             │
│        - Runs on timer (configurable interval)                   │
│        - Updates construction progress                           │
│        - Advances animation frames                               │
│        - Checks zombie/timeout conditions                        │
│                                                                  │
│  State Access Pattern:                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  WORLD STATE (asyncio.Lock)              │    │
│  │                                                           │    │
│  │  All state modifications acquire lock before writing.    │    │
│  │  Reads can proceed without lock (Python GIL provides     │    │
│  │  atomic reads for simple types).                         │    │
│  │                                                           │    │
│  │  Write Pattern:                                          │    │
│  │    async with world_state_lock:                           │    │
│  │        world_state.update_agent(agent_id, ...)           │    │
│  │        persistence.queue_write(agent_id, ...)             │    │
│  │                                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Persistence Pattern:                                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  WRITE-BEHIND QUEUE                      │    │
│  │                                                           │    │
│  │  State changes queue writes to persistence queue.        │    │
│  │  Background task drains queue and writes to SQLite.       │    │
│  │  This prevents blocking the event loop on I/O.           │    │
│  │                                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### State Synchronization

```
┌─────────────────────┐         ┌─────────────────────┐
│   In-Memory State   │         │   SQLite Database   │
│   (World State)     │         │   (Persistence)      │
├─────────────────────┤         ├─────────────────────┤
│                     │  Load   │                     │
│                     │◄────────│  Projects           │
│                     │         │  Villages           │
│                     │         │  Agents             │
│                     │         │  Structures         │
│                     │         │                     │
│                     │  Store  │                     │
│                     │────────►│  (Write-behind      │
│                     │         │   queue)            │
│                     │         │                     │
└─────────────────────┘         └─────────────────────┘

Load: On startup, read all state from SQLite into memory.
Store: On state change, queue write to SQLite (async).
```

## Design Tensions

### Tension 1: Event Inference Accuracy vs. Simplicity

**Problem:** Agent spawning and relationships must be inferred from tool patterns, but complex inference is computationally expensive and error-prone.

**Options:**

| Approach | Tradeoff |
|----------|----------|
| Simple pattern matching (concurrent tool calls = spawn) | Fast, but may miss spawns or create false positives |
| Session/task ID tracking with heuristics | More accurate, but requires maintaining complex state |
| Machine learning on tool patterns | Most accurate, but adds complexity and dependency |

**Resolution:** Start with simple pattern matching for MVP. Track session_id and tool_name sequences. Flag potential spawns when:
- Same session has overlapping tool calls (PreToolUse without corresponding PostToolUse)
- New session_id appears (may indicate spawned agent)

Document that inference accuracy will improve over iterations.

### Tension 2: Visual Fidelity vs. Performance

**Problem:** High event throughput could overwhelm rendering, but the user wants "frenetic" visual activity.

**Options:**

| Approach | Tradeoff |
|----------|----------|
| Render every event immediately | Most visually interesting, but may cause lag |
| Debounce rendering to 30 FPS | Smooth animation, but events may queue up |
| Aggregate events per frame | Consistent performance, but loses some visual detail |

**Resolution:** Implement frame-based rendering at 30 FPS. Queue incoming events, process all queued events each frame. This creates a "catch-up" effect during bursts while maintaining smooth animation. The visual interest goal (guiding principle 1) is preserved through the volume of events, not individual event rendering.

### Tension 3: World Size vs. Memory

**Problem:** The world can grow indefinitely as projects accumulate, but memory is finite.

**Options:**

| Approach | Tradeoff |
|----------|----------|
| Keep entire world in memory | Fast access, but unbounded memory growth |
| Page villages on demand | Bounded memory, but complex implementation |
| Limit world size (cap villages) | Simple, but loses persistence goal |

**Resolution:** Keep all villages in memory for MVP. Each village has bounded size (agents max out at active sessions, structures max out at density limit). SQLite persistence allows cold-start reload. If memory becomes an issue in production, implement lazy loading for inactive villages.

### Tension 4: Deterministic vs. Interesting Agent Placement

**Problem:** Agents should spawn near parents (deterministic), but too much clustering creates boring visuals.

**Options:**

| Approach | Tradeoff |
|----------|----------|
| Always spawn adjacent to parent | Deterministic, but creates tight clusters |
| Spawn within radius of parent | Some spread, but may overlap structures |
| Spawn on nearest empty cell | Flexible, but requires pathfinding |

**Resolution:** Spawn agents on nearest empty cell within a configurable radius (default: 3 cells) of parent position. This creates visual spread while maintaining parent-child proximity. The algorithm is deterministic (same parent + same world state = same spawn position), satisfying guiding principle 6.

### Tension 5: Real-time vs. Persistent State

**Problem:** Events arrive in real-time, but world state must persist across restarts. SQLite writes are slow.

**Options:**

| Approach | Tradeoff |
|----------|----------|
| Synchronous SQLite writes | Consistent, but blocks event processing |
| Write-behind queue | Fast, but may lose recent events on crash |
| In-memory only | Fastest, but no persistence |

**Resolution:** Write-behind queue with periodic checkpoint. Queue writes to a background task. On graceful shutdown, flush all pending writes. On crash, at most one checkpoint interval of events is lost. This balances performance (guiding principle 7: graceful degradation) with persistence (guiding principle 5).

## SQLite Schema

```sql
-- Projects: Each Claude Code project/codebase
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config_json TEXT NOT NULL,  -- JSON blob of ProjectConfig
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Sessions: Claude Code sessions (may have multiple per project)
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    started_at TEXT NOT NULL,
    last_activity TEXT NOT NULL,
    agent_ids_json TEXT NOT NULL  -- JSON array of agent IDs
);

-- Villages: One per project
CREATE TABLE villages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE REFERENCES projects(id),
    name TEXT NOT NULL,
    center_x INTEGER NOT NULL,
    center_y INTEGER NOT NULL,
    bounds_min_x INTEGER NOT NULL,
    bounds_min_y INTEGER NOT NULL,
    bounds_max_x INTEGER NOT NULL,
    bounds_max_y INTEGER NOT NULL
);

-- Agents: All agents ever seen
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    village_id TEXT NOT NULL REFERENCES villages(id),
    parent_id TEXT REFERENCES agents(id),
    inferred_type TEXT NOT NULL,
    color TEXT NOT NULL,
    position_x INTEGER NOT NULL,
    position_y INTEGER NOT NULL,
    last_seen TEXT NOT NULL,
    state TEXT NOT NULL,  -- 'active', 'idle', 'zombie'
    current_activity TEXT,
    total_work_units INTEGER NOT NULL DEFAULT 0
);

-- Structures: Built structures in villages
CREATE TABLE structures (
    id TEXT PRIMARY KEY,
    village_id TEXT NOT NULL REFERENCES villages(id),
    type TEXT NOT NULL,
    position_x INTEGER NOT NULL,
    position_y INTEGER NOT NULL,
    stage INTEGER NOT NULL,
    material TEXT NOT NULL,
    work_units INTEGER NOT NULL DEFAULT 0,
    work_required INTEGER NOT NULL
);

-- Event Log: Recent events for display (capped size)
CREATE TABLE event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    hook_type TEXT NOT NULL,
    tool_name TEXT,
    summary TEXT NOT NULL
);

-- World Metadata: Global state
CREATE TABLE world_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- Keys: 'viewport_center_x', 'viewport_center_y', 'last_sequence'

-- Indexes for common queries
CREATE INDEX idx_agents_village ON agents(village_id);
CREATE INDEX idx_agents_session ON agents(session_id);
CREATE INDEX idx_structures_village ON structures(village_id);
CREATE INDEX idx_event_log_timestamp ON event_log(timestamp);
```

## Hook Script Protocol

### Hook Script Structure

Each hook type has a corresponding script. All scripts:

1. Read JSON input from stdin
2. Extract minimal telemetry
3. Read project config from `.hamlet/config.json` in working directory (or parents)
4. Send to MCP server via JSON-RPC
5. Exit immediately (no retry, no blocking)

### PreToolUse Script

```python
#!/usr/bin/env python3
"""Hamlet PreToolUse hook - fires before tool execution."""
import json
import sys
import os
from pathlib import Path

def find_config(start_path: Path) -> dict | None:
    """Find .hamlet/config.json in current or parent directories."""
    current = start_path.resolve()
    while current != current.parent:
        config_path = current / ".hamlet" / "config.json"
        if config_path.exists():
            return json.loads(config_path.read_text())
        current = current.parent
    return None

def main():
    # Read hook input
    hook_input = json.load(sys.stdin)
    
    # Get project config
    working_dir = os.environ.get("CLAUDE_WORKING_DIR", ".")
    config = find_config(Path(working_dir)) or {}
    
    # Extract minimal telemetry
    event = {
        "jsonrpc": "2.0",
        "method": "hamlet/event",
        "params": {
            "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
            "timestamp": hook_input.get("timestamp", ""),
            "hook_type": "PreToolUse",
            "project_id": config.get("project_id", "default"),
            "project_name": config.get("project_name", "Unknown Project"),
            "data": {
                "tool_name": hook_input.get("data", {}).get("tool_name"),
                "tool_input": hook_input.get("data", {}).get("tool_input", {}),
            }
        }
    }
    
    # Send to MCP server (fire-and-forget)
    # ... MCP client code ...

if __name__ == "__main__":
    main()
```

### PostToolUse Script

Similar structure, but includes tool output and success status.

### Notification Script

Similar structure, but includes notification type and message.

### Stop Script

Similar structure, but includes stop reason and final stats.

## Agent Type Inference Rules

Agent types are inferred from tool usage patterns:

```typescript
// Inference rules (simplified for MVP)
const INFERENCE_RULES: InferenceRule[] = [
  {
    pattern: { tool_name: ["Read", "Grep"], frequency: "high" },
    inferred_type: "researcher",
    color: "cyan"
  },
  {
    pattern: { tool_name: ["Write", "Edit"], frequency: "high" },
    inferred_type: "coder",
    color: "yellow"
  },
  {
    pattern: { tool_name: ["Bash"], frequency: "high" },
    inferred_type: "executor",
    color: "green"
  },
  {
    pattern: { tool_name: ["Glob"], frequency: "high" },
    inferred_type: "explorer",
    color: "magenta"
  },
  {
    pattern: { tool_name: "any", frequency: "mixed" },
    inferred_type: "general",
    color: "white"
  }
];
```

Type is determined by analyzing tool frequency over a sliding window of recent events. Types can change as patterns evolve.

## Structure Type Mapping

Tool activity maps to structure types:

```typescript
const TOOL_TO_STRUCTURE: Record<string, StructureType> = {
  "Read": "library",      // Reading -> knowledge buildings
  "Grep": "library",
  "Glob": "library",
  "Write": "workshop",    // Writing -> production buildings
  "Edit": "workshop",
  "Bash": "forge",        // Execution -> action buildings
};
```

Construction progress accumulates per structure type based on tool duration:
- Each PostToolUse adds work_units proportional to duration_ms
- Structure stage advances at thresholds (100, 500, 1000 units)
- Material evolves: wood -> stone at stage 2, stone -> brick at stage 3

## 100% Coverage Check

| Module | Scope | Coverage |
|--------|-------|----------|
| MCP Server | MCP protocol, event reception | Hook scripts → Server |
| Event Processing | Normalization, routing | Server → Inference/State |
| Agent Inference | Lifecycle detection, typing | Events → Agent state |
| World State | Data model, CRUD | All entity operations |
| Simulation | Game loop, progression | World evolution |
| Viewport | Coordinates, scrolling | World → Screen |
| TUI | Rendering, input | Screen → User |
| Persistence | SQLite, serialization | State ↔ Disk |

**Gap Analysis:**
- Hook Scripts: Covered separately (external scripts, not module)
- Config Management: Covered by Persistence (project config storage)
- Error Handling: Covered by MCP Server (validation) and guiding principle 7 (graceful degradation)

**Overlap Check:**
- Agent positions: Owned by World State, used by Viewport (read-only)
- Event log: Owned by World State, used by TUI (read-only)
- No overlapping responsibilities detected.

**Coverage Statement:** All aspects of the system are covered by exactly one module. Cross-cutting concerns (config, error handling) are delegated to specific modules with clear ownership.

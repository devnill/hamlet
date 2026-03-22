# Spec Adherence Review — Cycle 001

## Architecture Deviations

### D1: MCPServer implements HTTP endpoint directly rather than stdio MCP transport
- **Expected**: Architecture specifies stdio_server transport for MCP protocol (MCP Server module design notes show `async with stdio_server() as (read_stream, write_stream)`)
- **Actual**: `MCPServer` uses aiohttp HTTP server (`/hamlet/event`, `/hamlet/health`, `/hamlet/state`, `/hamlet/terrain/{x}/{y}`) instead of stdio transport for event reception
- **Evidence**: `src/hamlet/mcp_server/server.py:79-101` — HTTP routes registered with aiohttp.web.Application rather than stdio MCP transport

### D2: PersistenceFacade interface differs from Persistence module spec
- **Expected**: Module spec defines `Persistence` class with methods `async save_project()`, `async save_session()`, etc.
- **Actual**: Implementation uses `PersistenceFacade` class with `queue_write()`, `delete_agent()`, `append_event_log()` methods; no direct `save_*` methods
- **Evidence**: `src/hamlet/persistence/facade.py:255-341` — `queue_write()` method queues operations; entity-specific save methods not exposed on facade

### D3: SimulationEngine tick loop delegates to separate updater classes not in spec
- **Expected**: Module spec shows SimulationEngine directly implementing `_update_agents()`, `_update_structures()` methods
- **Actual**: SimulationEngine delegates to `AgentUpdater`, `StructureUpdater`, `ExpansionManager`, `AnimationManager` classes
- **Evidence**: `src/hamlet/simulation/engine.py:84-127` — tick calls `self._agent_updater.update_agents()`, `self._structure_updater.update_structures()`, `self._expansion_manager.process_expansion()`, `self._animation_manager.advance_frames()`

## Unmet Acceptance Criteria

None. All acceptance criteria in the reviewed work items (WI-213 through WI-231) have been verified as met through the incremental review process.

## Principle Violations

None. All guiding principles are adhered to in the implementation.

## Principle Adherence Evidence

- Principle 1 — Visual Interest Over Accuracy: `src/hamlet/tui/symbols.py` defines ASCII symbols and TYPE_COLORS mapping; `src/hamlet/tui/world_view.py:130-134` renders spinning animation for active agents
- Principle 2 — Lean Client, Heavy Server: Hook scripts in `src/hamlet/hooks/` are minimal (<100 lines each), only extract telemetry and POST to HTTP endpoint
- Principle 3 — Thematic Consistency: `src/hamlet/tui/symbols.py:14-27` defines TYPE_COLORS with semantic mappings (cyan=research, yellow=construction, green=execution, magenta=planning, blue=verification)
- Principle 4 — Modularity for Iteration: `src/hamlet/world_state/rules.py:11-28` defines `TYPE_RULES` as a list of tuples for easy modification; `TOOL_TO_STRUCTURE` mapping in same file is swappable
- Principle 5 — Persistent World, Project-Based Villages: `src/hamlet/world_state/manager.py:61-182` loads state from persistence on startup; villages are project-scoped via `village.project_id`
- Principle 6 — Deterministic Agent Identity: `src/hamlet/inference/types.py:56-61` defines `TYPE_COLORS` mapping; `src/hamlet/inference/engine.py:298-302` applies color from inferred type
- Principle 7 — Graceful Degradation Over Robustness: `src/hamlet/mcp_server/server.py:71-74` catches exceptions on MCP start and logs instead of crashing; `src/hamlet/event_processing/event_processor.py:229-230` logs and continues on event processing failures
- Principle 8 — Agent-Driven World Building: `src/hamlet/inference/engine.py:309-318` adds work units on PostToolUse; `src/hamlet/simulation/structure_updater.py` advances structure stages based on work units
- Principle 9 — Parent-Child Spatial Relationships: `src/hamlet/inference/engine.py:162-195` spawns new agents near parent; `src/hamlet/world_state/manager.py:679-722` implements `find_spawn_position()` with parent proximity preference
- Principle 10 — Scrollable World, Visible Agents: `src/hamlet/viewport/manager.py:94-106` implements scroll and set_center methods; `src/hamlet/tui/app.py:102-115` defines hjkl and arrow key bindings for scrolling
- Principle 11 — Low-Friction Setup: `src/hamlet/cli/commands/install.py` provides single-command hook setup; `src/hamlet/cli/commands/init.py` initializes config; Settings auto-detects defaults

## Undocumented Additions

### U1: RemoteWorldState and RemoteStateProvider for viewer mode
- **Location**: `src/hamlet/tui/remote_state.py`, `src/hamlet/tui/remote_world_state.py`
- **Description**: HTTP client implementation for connecting viewer to running daemon; not described in architecture but essential for daemon/viewer split
- **Risk**: Low — enables the viewer mode architecture described in WI-127, extends WorldStateProtocol correctly

### U2: ActivitySummarizer for LLM-based activity summarization
- **Location**: `src/hamlet/inference/summarizer.py`
- **Description**: Uses LLM to generate `current_activity` text for agents based on tool input; WI-111 specifies this but not in architecture module specs
- **Risk**: Low — properly integrated into AgentInferenceEngine as optional dependency

### U3: daemon and service CLI subcommands
- **Location**: `src/hamlet/cli/commands/daemon.py`, `src/hamlet/cli/commands/service.py`
- **Description**: CLI commands for daemon mode and launchd service management; WI-126, WI-127, WI-204 define these but they are not in architecture
- **Risk**: Low — properly structured under cli/commands package

### U4: Terrain module
- **Location**: `src/hamlet/world_state/terrain.py`
- **Description**: Terrain generation and caching; documented in `specs/plan/modules/terrain.md` module spec but not in the main architecture diagram
- **Risk**: None — properly follows module spec with TerrainType, TerrainGenerator, TerrainGrid classes

## Naming/Pattern Inconsistencies

### N1: AgentType enum includes PLANNER not in module spec
- **Convention**: Module spec (Agent Inference) lists RESEARCHER, CODER, EXECUTOR, ARCHITECT, TESTER, GENERAL
- **Violation**: `src/hamlet/world_state/types.py:10-18` — AgentType includes PLANNER (between EXECUTOR and ARCHITECT) not mentioned in spec
- **Note**: This is likely an intentional addition during implementation; `inference/rules.py` also references PLANNER type rules

### N2: HookType enum values differ from architecture examples
- **Convention**: Architecture (MCP Server module) shows `hook_type` enum values: PreToolUse, PostToolUse, Notification, Stop
- **Violation**: `src/hamlet/event_processing/internal_event.py:5-23` — HookType enum includes 15 hook types (SessionStart, SessionEnd, SubagentStart, SubagentStop, TeammateIdle, TaskCompleted, PostToolUseFailure, UserPromptSubmit, PreCompact, PostCompact, StopFailure in addition to original 4)
- **Note**: Intentional expansion per WI-179, WI-180, WI-181, WI-182 — new hook scripts added for v0.4.0

### N3: WorldStateProtocol methods differ from WorldStateManager public interface
- **Convention**: Protocol should match implementation interface
- **Violation**: `src/hamlet/protocols.py:24-58` — WorldStateProtocol defines subset of WorldStateManager methods; some methods like `get_viewport_center()`, `update_viewport_center()` exist on manager but not protocol
- **Note**: Acceptable — protocols.py documents "interface that consumers depend on" rather than complete public API

## Summary

The implementation closely follows the architecture with only minor deviations:

1. **HTTP vs stdio transport for MCP** (D1): The architecture showed stdio MCP transport, but implementation uses HTTP endpoints. This is a pragmatic decision for hook scripts which can easily POST JSON.

2. **Persistence facade pattern** (D2): The implementation uses a cleaner facade pattern with write-behind queue rather than direct save methods. This is an architectural refinement.

3. **Delegated simulation** (D3): SimulationEngine delegates to specialized updater classes. This is good modularity (GP-4) even if not explicitly shown in the spec diagram.

4. **Undocumented additions** (U1-U4): All additions serve specific features (viewer mode, activity summary, daemon/service mode, terrain) and are either specified in later work items or properly documented in module specs.

5. **Naming variations** (N1-N3): Minor differences in enum values and protocol completeness; all are intentional expansions or acceptable simplifications.

All guiding principles are satisfied. No acceptance criteria are unmet. The implementation demonstrates strong adherence to the architecture and principles while making reasonable refinements for practical implementation concerns.

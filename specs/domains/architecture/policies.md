# Policies: Architecture

## P-1: Lean Client, Heavy Server
Hook scripts must do minimal processing — just enough to extract essential telemetry. All inference, state management, and business logic happen server-side.

- **Derived from:** GP-2 (Lean Client, Heavy Server)
- **Established:** planning phase
- **Status:** active

## P-2: Async-First Design
All modules use asyncio. The TUI, MCP server, simulation, and event processing run as concurrent tasks in a single event loop. No blocking I/O.

- **Derived from:** GP-2 (Lean Client, Heavy Server), GP-7 (Graceful Degradation)
- **Established:** planning phase
- **Status:** active

## P-3: Write-Behind Persistence
State changes queue writes to SQLite without blocking. A background task drains the queue. This prevents blocking the UI on I/O.

- **Derived from:** GP-5 (Persistent World), GP-7 (Graceful Degradation)
- **Established:** planning phase
- **Status:** active

## P-4: Single Process Architecture
The MCP server, TUI, and simulation run in a single process. No inter-process communication overhead.

- **Derived from:** Technology decision
- **Established:** planning phase
- **Status:** active

## P-5: Hook scripts must read event data from stdin
Hook scripts must read Claude Code hook data via `json.load(sys.stdin)` and extract `tool_name`, `tool_input`, `tool_output`, `success`, and `duration_ms` from the parsed JSON. Environment variables like `CLAUDE_TOOL_NAME` are not Claude Code variables and must not be used as data sources.

- **Derived from:** D-4, archive/cycles/003/gap-analysis.md (G3), archive/cycles/003/spec-adherence.md (C1, C3)
- **Established:** cycle 003
- **Status:** active

## P-6: Hook scripts must read project identity from config file traversal
Hook scripts must implement `find_config()` — traversing from `os.getcwd()` upward to find `.hamlet/config.json` — and read `project_id` and `project_name` from it. Fabricated environment variables (`CLAUDE_PROJECT_ID`, `CLAUDE_SESSION_ID`) must not be used. Fallback should be a deterministic hash of the working directory path, not the string `"unknown"`.

- **Derived from:** D-4, archive/cycles/003/gap-analysis.md (G4), archive/cycles/003/spec-adherence.md (C2)
- **Established:** cycle 003
- **Status:** active

## P-7: Configurable mapping dicts must live in a single canonical module
All configurable mapping dictionaries (`STRUCTURE_RULES`, `TOOL_TO_STRUCTURE`, `TYPE_RULES`) must be defined in their canonical module (e.g., `world_state/rules.py`) and imported elsewhere. No local copies of mappings in consuming modules.

- **Derived from:** archive/cycles/003/code-quality.md (S1), archive/cycles/003/spec-adherence.md (S1)
- **Established:** cycle 003
- **Status:** active

## P-8: Hook scripts must use flat params format (no nested "data" sub-object)
Event-specific fields (`tool_name`, `tool_input`, `tool_output`, `success`, `duration_ms`, `notification_message`, `stop_reason`) must be flat siblings of `session_id` and `hook_type` within `params`. No nesting under a `"data"` sub-object. The EventProcessor, hook scripts, and architecture contract all use this format.

- **Derived from:** D-9, archive/cycles/004/decision-log.md (D1), archive/cycles/004/code-quality.md (S2)
- **Established:** cycle 004
- **Status:** active

## P-9: Hook port propagation — any fix must wire configured mcp_port to hook scripts
Hook scripts must not hardcode the server port. Any mechanism for port configurability must propagate `settings.mcp_port` to hook scripts at install time or runtime. The server-side port is configurable; the hook-side port must match.

- **Derived from:** D-11, archive/cycles/004/gap-analysis.md (II1), archive/cycles/004/decision-log.md (D11)
- **Established:** cycle 004
- **Status:** active
- **Amended:** cycle 005 — implemented via config file: `install_command` writes `server_url` to `~/.hamlet/config.json`; hooks read it via `find_server_url()`. See D-13.

## P-10: Symbol removal must audit the test tree before closing
When a symbol is deleted or removed from a source module — whether by deleting the module entirely or by removing an export from it — the `tests/` directory must be grep-checked for imports of that symbol before the work item is considered complete. A source-only caller audit is insufficient.

- **Derived from:** D-15, archive/cycles/005/decision-log.md (D3, CR1), archive/cycles/005/code-quality.md (C1)
- **Established:** cycle 005
- **Status:** active
- **Amended:** cycle 006 — scope broadened from "dead-code module deletion" to "any symbol removal." WI-123 removed `AGENT_BASE_COLORS` from `animation.py` (not a module deletion) and broke `test_animation.py` at import — same pattern as cycle 005. See archive/cycles/006/gap-analysis.md (SG1), archive/cycles/006/decision-log.md (D-R2, CR1).

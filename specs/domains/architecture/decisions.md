# Decisions: Architecture

## D-1: Python/Textual Stack
- **Decision:** Use Python with Textual framework for the TUI, official Python MCP SDK for server integration.
- **Rationale:** Async-native architecture matches MCP's async nature, hot reload enables rapid iteration, official SDK support.
- **Assumes:** Python 3.11+ available.
- **Source:** plan/architecture.md
- **Status:** settled

## D-2: Single Persistent MCP Server
- **Decision:** One server process receives events from multiple Claude Code sessions. SQLite stores world state.
- **Rationale:** Global world map tracking all projects requires shared state. Multiple sessions must see same villages.
- **Assumes:** Single-machine deployment acceptable.
- **Source:** steering/interview.md
- **Status:** settled

## D-3: Concurrent Task Architecture
- **Decision:** TUI, MCP server, simulation, and event processing run as asyncio tasks in single process.
- **Rationale:** Eliminates IPC overhead, shares state in-memory, fits async-native Textual model.
- **Source:** plan/architecture.md
- **Status:** settled

## D-4: Hook scripts excluded from Cycle 003 scope
- **Decision:** Hook scripts were treated as complete after Cycle 002 (WI-090, WI-091) and excluded from Cycle 003 refinement scope.
- **Rationale:** The HTTP endpoint addition (WI-100) was considered sufficient; hooks were assumed correct.
- **Assumes:** Hooks were functional after Cycle 002. This assumption proved false.
- **Source:** archive/cycles/003/decision-log.md (D43)
- **Status:** settled
- **Note:** This scoping decision caused all hook defects (stdin not read, fabricated env vars, missing fields) to survive into Cycle 004.

## D-5: aiohttp added; HTTP and stdio transports coexist
- **Decision:** `aiohttp>=3.9.0` added as runtime dependency for the HTTP event endpoint. The pre-existing stdio MCP transport was not removed.
- **Rationale:** Hook scripts need an HTTP POST target. Stdio transport was left in place rather than removed.
- **Source:** archive/cycles/003/decision-log.md (D46)
- **Status:** superseded by D-12
- **Note:** Stdio transport removed in cycle 004 (D-12).

## D-6: LLM activity summarizer added with claude-haiku-4-5
- **Decision:** WI-111 added an `ActivitySummarizer` using `claude-haiku-4-5-20251001` via the `anthropic` Python package. Configured as fire-and-forget `asyncio.create_task` (not inline await) to avoid blocking the event pipeline.
- **Rationale:** Inline await could block event processing for up to 5 seconds per event. Fire-and-forget avoids pipeline stalls.
- **Source:** archive/cycles/003/decision-log.md (D45, D56)
- **Status:** settled
- **Note:** Task reference is not retained in a set, creating a theoretical GC risk (code-quality M3).

## D-7: mcp_port setting validated but not wired to HTTP server
- **Decision:** `Settings.mcp_port` is validated (type check, range check, bool exclusion) but `MCPServer` hardcodes port 8080. The setting has no runtime effect.
- **Rationale:** WI-112 (config validation) and WI-100 (HTTP endpoint) were scoped independently; neither included wiring. Planning-level gap.
- **Source:** archive/cycles/003/decision-log.md (D58); archive/cycles/003/code-quality.md (S4)
- **Status:** superseded by D-11
- **Note:** Wired in cycle 004 (D-11).

## D-8: Hook event fields sent flat, not nested under `data`
- **Decision:** Hook scripts send tool-specific fields (`tool_name`, `tool_input`, etc.) flat at the params level. The architecture HookEvent contract specifies nesting under a `data` sub-object. The `EventProcessor` reads the flat format. The implementation is internally consistent but diverges from the written contract.
- **Rationale:** Rationale not recorded. The flat format was implemented; the contract was not updated.
- **Source:** archive/cycles/003/spec-adherence.md (C3); archive/cycles/003/summary.md
- **Status:** superseded by D-9
- **Note:** Resolved in cycle 004. Flat format adopted as canonical (D-9).

## D-9: Flat HookEvent params format adopted as canonical contract
- **Decision:** Event-specific fields (`tool_name`, `tool_input`, `tool_output`, `success`, `duration_ms`, `notification_message`, `stop_reason`) are flat siblings of `session_id` and `hook_type` within `params`. The `architecture.md` contract was updated to match. The `validation.py` EVENT_SCHEMA was not updated and retains a stale nested `"data"` block.
- **Rationale:** Implementation, hooks, and EventProcessor all use flat format. The nested `"data"` contract was never implemented in any consumer. Aligning the spec to reality.
- **Source:** archive/cycles/004/decision-log.md (D1); archive/cycles/004/code-quality.md (S2)
- **Policy:** P-8
- **Status:** settled

## D-10: TOOL_TO_STRUCTURE relocated to world_state/rules.py
- **Decision:** `TOOL_TO_STRUCTURE` mapping moved from inference modules to `world_state/rules.py`, co-located with `STRUCTURE_RULES`. Prior cycle claimed this was done; cycle 004 (WI-117) corrected the oversight.
- **Rationale:** Enforces P-7 (configurable mapping dicts in a single canonical module).
- **Source:** archive/cycles/004/decision-log.md (D12)
- **Status:** settled

## D-11: MCPServer port parameter wired to settings.mcp_port
- **Decision:** `server.py` now accepts a `port` parameter from `settings.mcp_port`. Install health check uses configured port. Hook scripts remain hardcoded to 8080.
- **Rationale:** Closes the server-side port configurability gap (Q-4). Hook-side gap tracked separately (Q-7).
- **Source:** archive/cycles/004/decision-log.md (D11); archive/cycles/004/gap-analysis.md (II1)
- **Status:** settled

## D-12: stdio MCP transport removed from server.py
- **Decision:** `_run_server` method, `asyncio.create_task`, `stdio_server` import, and `_run_task` handling all deleted. HTTP-only transport remains.
- **Rationale:** Hook scripts use HTTP exclusively. The stdio server ran as a dead background task waiting on stdin that never arrives.
- **Source:** archive/cycles/004/decision-log.md (D14)
- **Status:** settled

## D-13: Hook server URL moved to config-driven fix (no hardcoded port)
- **Decision:** `install_command` writes `server_url` to `~/.hamlet/config.json`. Hook scripts read it at startup via `find_server_url()`. No port is hardcoded in any hook script.
- **Rationale:** Satisfies GP-11 (low-friction setup). Config-driven approach preferred over a targeted port substitution because it ensures the correct port is always used regardless of `mcp_port` setting value.
- **Assumes:** `install_command` is run before hooks are invoked.
- **Source:** archive/cycles/005/decision-log.md (D1); archive/cycles/005/summary.md
- **Status:** settled

## D-14: EVENT_SCHEMA dead nested "data" block removed; flat schema adopted
- **Decision:** `validation.py` EVENT_SCHEMA rewritten with all event-specific fields as flat properties directly under `params`. The stale nested `"data"` sub-object block was removed. `architecture.md` HookEvent interface updated with a note confirming flat format is canonical.
- **Rationale:** The nested `"data"` block documented a structure that no real payload ever contained. All event-specific fields were passing schema validation unchecked because the actual flat fields were outside the schema's validated scope.
- **Source:** archive/cycles/005/decision-log.md (D5); archive/cycles/005/spec-adherence.md
- **Status:** settled

## D-15: Dead-code deletion scope must include the test tree
- **Decision:** When source files are deleted as dead code (WI-119 deleted `inference/colors.py`), the tests/ directory must be audited for imports of the deleted module before closing the work item. The WI-119 audit checked `src/hamlet/` only; `tests/test_zombie_detection.py` imported the deleted module and crashed at collection, eliminating all zombie detection test coverage.
- **Rationale:** Incremental review audited production callers but not test callers. The critical finding (C1) was caught only in the final cycle review, requiring rework.
- **Policy:** P-10
- **Source:** archive/cycles/005/decision-log.md (D3, CR1); archive/cycles/005/code-quality.md (C1)
- **Status:** settled

## D-16: notification_message and stop_reason consumed in engine and event log
- **Decision:** `engine._handle_notification()` logs `notification_message` when non-None. `engine._handle_stop()` logs `stop_reason` when non-None. `manager.handle_event()` builds event log summary unconditionally using hook-type routing with `or ''` fallback, so Notification and Stop events always produce correctly prefixed summaries.
- **Rationale:** Fields were extracted in cycle 005 (WI-120) but consumed nowhere downstream. WI-122 closes that gap. Behavioral differentiation on `stop_reason` value remains deferred.
- **Source:** archive/cycles/006/decision-log.md (D-E7, D-R1)
- **Status:** settled

## D-17: find_config() skips configs lacking project_id key
- **Decision:** Guard `if "project_id" not in data: continue` added in all four hook scripts. Direct key access `data["project_id"]` replaces `.get()` fallback (dead code after the guard). Global `~/.hamlet/config.json` (which contains `server_url` but not `project_id`) is now transparent to project config lookup.
- **Rationale:** Without the guard, `find_config()` traversal reached `~/.hamlet/config.json` for most users, causing the home directory basename to appear as project name.
- **Source:** archive/cycles/006/decision-log.md (D-E9, D-E10)
- **Status:** settled

## D-18: stop_reason behavioral differentiation deferred
- **Decision:** Both `stop_reason` values ("stop" for clean termination, "tool" for mid-tool interruption) receive identical treatment in `_handle_stop()`. Differentiation deferred pending a design decision on interrupted-session state semantics.
- **Rationale:** Zombie eviction handles stale pending_tools entries regardless of stop reason via TTL. Proactive differentiation requires defining what "interrupted" means for agent state transitions.
- **Source:** archive/cycles/006/decision-log.md (D-R3); archive/cycles/006/gap-analysis.md (MG1)
- **Status:** settled

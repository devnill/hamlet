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

## D-19: os.chdir(cwd) required before find_server_url() and find_config() in all hook scripts
- **Decision:** All hook scripts must call `os.chdir(hook_input.get("cwd", ""))` after reading stdin and before calling `find_server_url()` or `find_config()`. Both utility functions traverse from `os.getcwd()`; without chdir, traversal starts from Claude Code's launch directory. Five WI-180 hooks omitted this step and were fixed during review.
- **Rationale:** WI-179 hooks included the chdir pattern from rework; WI-180 hooks were completed before the pattern was established. The capstone review (S1) caught the omission.
- **Source:** archive/cycles/008/decision-log.md (decision 1), archive/cycles/008/code-quality.md (S1)
- **Policy:** Amends P-6
- **Status:** settled

## D-20: HOOK_SCRIPTS dict must cover all registered hook types
- **Decision:** `HOOK_SCRIPTS` in `install.py` must list all hook types and their script filenames, matching `hooks.json`. When WI-185 was implemented, the dict still listed only the original 4 hooks. Non-plugin users running `hamlet install` received only 4 of 15 hooks. Fixed during cycle 008 review.
- **Rationale:** Non-plugin users rely entirely on `hamlet install` for hook registration. Missing entries cause silent degraded experience.
- **Source:** archive/cycles/008/code-quality.md (M4), archive/cycles/008/gap-analysis.md (G1)
- **Policy:** P-11
- **Status:** settled

## D-21: PreToolUse and PreCompact are blocking hooks — no async:true
- **Decision:** Blocking hooks (PreToolUse, PreCompact) must not have `"async": true` in `hooks.json`. All other 13 hook types use `"async": true`. Setting async on a blocking hook causes a Claude Code load error.
- **Rationale:** Claude Code specification requires blocking hooks to run synchronously so they can interrupt processing.
- **Source:** archive/cycles/008/decision-log.md (decision 3)
- **Status:** settled

## D-22: TeammateIdle handler is log-only — no agent name lookup
- **Decision:** The TeammateIdle daemon handler logs a summary string only and performs no state mutation. The `Agent` dataclass has no `name` field, so `getattr(agent, "name", None)` always returns None and no teammate-to-agent resolution is possible.
- **Rationale:** No stored mapping from teammate name to Agent entity exists in the data model. Adding one would require an Agent.name field or a name-to-agent_id index.
- **Source:** archive/cycles/008/decision-log.md (decision 4)
- **Status:** settled

## D-23: stop_failure.py nested error object accepted as P-8 asymmetry
- **Decision:** `stop_failure.py` sends `"error": {"type": ..., "reason": ...}` as a nested object within params. This is the only hook that sends a nested non-tool value. The schema explicitly permits it (`"error": {"type": ["object", "null"]}`) and `InternalEvent` stores it as `dict[str, Any] | None`. Accepted as an asymmetry rather than a P-8 violation.
- **Rationale:** The nested structure matches the Claude Code hook payload format. Flattening would diverge from the source data shape for no pipeline benefit.
- **Source:** archive/cycles/008/code-quality.md (M1), archive/cycles/008/decision-log.md (decision 5)
- **Status:** settled

## D-24: min_village_distance moved to configurable Settings field
- **Decision:** `MIN_VILLAGE_DISTANCE = 15` moved from a `WorldStateManager` class constant to `Settings.min_village_distance: int = 15`, wired through `app_factory.py` (WI-264).
- **Rationale:** Exposes a tunable gameplay parameter without requiring code changes. Consistent with how other world parameters are managed.
- **Source:** archive/cycles/014/decision-log.md (D1)
- **Status:** settled

## D-25: Settings CLI uses dot notation for terrain sub-keys
- **Decision:** `hamlet settings set terrain.seed 42` uses `.` as a separator to address keys within the `terrain` sub-dict. Top-level keys use bare names. Implemented in WI-265.
- **Rationale:** The `terrain` field in `Settings` is a dict; dot notation provides a readable way to address nested keys without restructuring the CLI or the storage format.
- **Source:** archive/cycles/014/decision-log.md (D2)
- **Status:** settled

## D-26: settings set infers target type from current stored value
- **Decision:** `hamlet settings set` derives the expected type (int, float, bool, None) from the existing stored value rather than requiring callers to pass explicit type flags.
- **Rationale:** Avoids a verbose CLI interface. The existing value is the authoritative type declaration. If no value is stored yet, the behavior falls back to string.
- **Source:** archive/cycles/014/decision-log.md (D3)
- **Status:** settled

## D-27: Periodic config reload interval fixed at 30 seconds
- **Decision:** The daemon's config reload loop uses `RELOAD_INTERVAL = 30` as a module-level constant (WI-266). The interval is not itself user-configurable.
- **Rationale:** A fixed interval avoids the circularity of making the reload interval configurable via the mechanism it controls. 30 seconds is a reasonable balance between responsiveness and polling overhead.
- **Source:** archive/cycles/014/decision-log.md (D4)
- **Status:** settled

## D-28: Restart-required settings excluded from hot-reload
- **Decision:** `mcp_port`, `db_path`, and `terrain` are excluded from the daemon's periodic config reload. Changes to these fields are detected and logged as warnings; they do not take effect until the daemon is restarted.
- **Rationale:** These fields require subsystem initialization that cannot be done at runtime without tearing down and rebuilding the MCP server, database connection, or terrain generator. Hot-applying them would leave subsystems in an inconsistent state.
- **Source:** archive/cycles/014/decision-log.md (D5)
- **Policy:** P-13
- **Status:** settled

## D-29: _shutdown_requested flag reset at entry to _run_daemon
- **Decision:** `global _shutdown_requested; _shutdown_requested = False` added as the first statement in `_run_daemon`. The flag is a module-level boolean set by the signal handler; without a reset, a second invocation of `daemon_command` in the same Python process exits immediately without doing any work (pre-existing bug, fixed as rework in cycle 014).
- **Rationale:** Module-level signal handler flags persist across calls in the same process. Tests and any programmatic re-invocation require the flag to be in a known-False state at entry.
- **Source:** archive/cycles/014/code-quality.md (S1)
- **Policy:** P-14
- **Status:** settled

## D-30: Rendering layer scope boundary — core untouched by backend addition
- **Decision:** The daemon, event pipeline, WorldStateManager, persistence layer, and hooks were explicitly excluded from cycle 015 scope. The gui/ module is an isolated rendering layer that consumes world state read-only. New rendering backends must not modify core subsystems.
- **Rationale:** Adding a graphical backend does not require changes to event processing or state management. A hard scope boundary prevents accidental coupling between rendering and core.
- **Source:** archive/cycles/015/decision-log.md (D7)
- **Status:** settled

## D-31: Terminal routing — tmux uses Textual, capable terminals use notcurses
- **Decision:** When `settings.renderer = "auto"`, tmux sessions route to the Textual (ASCII) backend; capable terminals (those with notcurses available) route to the notcurses backend. No passthrough investigation was performed.
- **Rationale:** tmux does not support pixel-level blitters. Simple binary routing avoids complex capability probing while delivering the correct experience for the two primary terminal contexts.
- **Source:** archive/cycles/015/decision-log.md (D5)
- **Status:** superseded by D-32
- **Note:** Notcurses abandoned in cycle 016. Terminal routing is now: tmux → Textual; Kitty-capable terminal → KittyApp. See D-32.

## D-32: Terminal routing updated — tmux uses Textual, Kitty-capable terminals use KittyApp
- **Decision:** When `settings.renderer = "auto"`, tmux sessions route to the Textual backend; terminals that support the Kitty graphics protocol route to `KittyApp`. `detect.py`/`resolve_renderer` implements this routing. The design constraint is updated to require pure Python for any graphical backend — no C library, no ctypes, no subprocess isolation.
- **Rationale:** Notcurses abandoned (see visualization D-16). Kitty protocol is implemented via pure Python escape sequences — no library availability check is needed, only terminal capability detection. Pure Python eliminates the memory-safety risks that caused the notcurses segfault.
- **Source:** archive/cycles/016/decision-log.md (D1, D2); archive/cycles/016/spec-adherence.md
- **Status:** settled

## D-33: Rendering pipeline crash resolved at the parse layer, not the access layer
- **Decision:** The cycle 017 crash (`'dict' object has no attribute 'position'`) was fixed by making `StateFetcher.fetch_snapshot()` return typed `Agent`, `Structure`, and `Village` dataclasses. The alternative — adding `isinstance(v, dict)` guards at every access site in `app.py` — was rejected.
- **Rationale:** Parsing in the fetcher is architecturally correct: downstream code must never handle both raw dicts and typed objects simultaneously. Defensive guards at access sites preserve the root cause and mask future regressions.
- **Source:** archive/cycles/017/decision-log.md (D1)
- **Status:** settled

## D-34: Parse helpers shared between TUI and Kitty backends via cross-module import
- **Decision:** `StateFetcher` in `gui/kitty/state_fetcher.py` imports `_parse_agent`, `_parse_structure`, `_parse_village` from `tui/remote_world_state.py` rather than duplicating parse logic. The helpers are not in `__all__` and carry the `_` prefix.
- **Rationale:** GP-3 (Thematic Consistency) requires both backends to use the same domain model. The helpers already existed, were tested, and handled enum coercion correctly. Duplication would create divergent type coercion between TUI and Kitty.
- **Assumes:** The `tui/remote_world_state.py` module remains the authoritative location until helpers are promoted (see Q-22).
- **Source:** archive/cycles/017/decision-log.md (D2)
- **Status:** settled

## D-35: Per-item graceful degradation in Kitty parse path via _try_parse
- **Decision:** A local `_try_parse(fn, item)` helper in `state_fetcher.py` wraps each parse call. It returns `None` on any exception; walrus-operator list comprehensions filter `None` results. Valid items survive even when a neighbor is malformed.
- **Rationale:** GP-7 (Graceful Degradation) requires malformed items to be skipped without crashing. Per-item wrapping is finer-grained than the TUI path, which discards the entire category on a single failure. `_try_parse` catches bare `Exception` — see Q-22 for the promotion path that would allow tightening to specific exception types.
- **Source:** archive/cycles/017/decision-log.md (D3)
- **Status:** settled

## D-36: Integration tests for rendering pipelines must mock only the network transport boundary
- **Decision:** `tests/test_kitty_integration.py` patches only `urllib.request.urlopen` and lets the full pipeline run: JSON bytes → parse functions → typed dataclasses → `ViewportState` → `render_frame` → string output. Mocking at the dataclass level (as cycle 016 tests did) bypasses `StateFetcher` and cannot catch type mismatch crashes.
- **Rationale:** The cycle 016 ship-and-crash was caused by 169 passing unit tests that used mock dataclasses constructed directly, bypassing `StateFetcher` entirely. Moving the mock boundary to the network call exercises the same code path that runs in production.
- **Policy:** P-15
- **Source:** archive/cycles/017/decision-log.md (D5)
- **Status:** settled

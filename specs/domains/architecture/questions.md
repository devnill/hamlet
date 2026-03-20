# Questions: Architecture

## Q-1: Hook Script Deployment
- **Question:** How should users install hook scripts? Manual config editing, or automated setup command?
- **Source:** steering/interview.md
- **Impact:** Affects user onboarding complexity. Manual requires documenting config format; automated requires setup command in CLI.
- **Status:** resolved
- **Resolution:** An automated `hamlet install` command was implemented that writes hooks to Claude Code settings.
- **Resolved in:** cycle 002

## Q-2: MCP Server Discovery
- **Question:** How do hook scripts discover the MCP server address? Config file, environment variable, or hardcoded localhost?
- **Source:** plan/architecture.md
- **Impact:** Affects multi-machine deployment. Localhost assumes single machine.
- **Status:** resolved
- **Resolution:** Hook scripts POST to `http://localhost:8080/hamlet/event` (hardcoded). Server port is intended to be configurable via `mcp_port` setting but is not yet wired (see Q-4).
- **Resolved in:** cycle 003

## Q-3: Hook event field nesting format
- **Question:** Hook scripts send event fields flat in params (`params["tool_name"]`), while the architecture HookEvent contract specifies nesting under `data` (`params["data"]["tool_name"]`). The implementation is internally consistent with the flat format. Should the architecture contract be updated to match the flat format, or should hooks and EventProcessor be restructured to use the nested format?
- **Source:** archive/cycles/003/spec-adherence.md (C3); archive/cycles/003/summary.md
- **Impact:** Any future hook or EventProcessor code written to the spec will fail against live payloads if the contract is not aligned with implementation.
- **Status:** resolved
- **Resolution:** Flat format adopted as canonical. Architecture.md updated to specify flat params. See D-9.
- **Resolved in:** cycle 004

## Q-4: mcp_port setting not wired to HTTP server
- **Question:** `Settings.mcp_port` is validated but `MCPServer` hardcodes port 8080. Should `mcp_port` be wired to the server constructor, and should this be addressed in Cycle 004?
- **Source:** archive/cycles/003/code-quality.md (S4); archive/cycles/003/decision-log.md (D58)
- **Impact:** Users on systems where port 8080 is unavailable cannot reconfigure. The error message in `__main__.py` instructs users to change a setting that has no effect.
- **Status:** resolved
- **Resolution:** MCPServer now accepts port parameter from settings.mcp_port. Server-side port is configurable. Hook-side gap remains (Q-7).
- **Resolved in:** cycle 004

## Q-5: Stdio MCP transport retained as dead background task
- **Question:** `MCPServer.start()` starts both stdio MCP and HTTP listeners. Hook scripts use HTTP exclusively. The stdio server runs as a background task waiting on stdin that never arrives. Should the stdio transport be removed or gated behind a configuration flag?
- **Source:** archive/cycles/003/spec-adherence.md (M2); archive/cycles/003/decision-log.md (D46)
- **Impact:** Background task consuming event loop capacity indefinitely with no purpose.
- **Status:** resolved
- **Resolution:** stdio MCP transport removed from server.py entirely. HTTP-only transport remains. See D-12.
- **Resolved in:** cycle 004

## Q-6: /hamlet/health endpoint missing
- **Question:** `install.py` validates the MCP server by calling `http://localhost:8080/hamlet/health`, but the HTTP server registers only `/hamlet/event`. Should a GET `/hamlet/health` route be added?
- **Source:** archive/cycles/003/gap-analysis.md (G5)
- **Impact:** Every `hamlet install` run produces a misleading "MCP server not reachable" warning even when Hamlet is running. Violates GP-11 (low-friction setup).
- **Status:** open
- **Reexamination trigger:** Cycle 004 infrastructure work items.

## Q-7: Hook port hardcoding fix level
- **Question:** Hook scripts hardcode `SERVER_URL = "http://localhost:8080/hamlet/event"`. When `mcp_port != 8080`, install check passes but all events are silently dropped. Two options: (A) Full fix — add `server_url` to `~/.hamlet/config.json` written by `install.py`; hooks read it at startup. (B) Partial fix — warn in `install_command()` when `mcp_port != 8080`.
- **Source:** archive/cycles/004/gap-analysis.md (II1); archive/cycles/004/decision-log.md (OQ3)
- **Impact:** Critical. Silent event loss when port is reconfigured. GP-11 (Low-Friction Setup) violation.
- **Status:** resolved
- **Resolution:** Full fix implemented (option A). `install_command` writes `server_url` to `~/.hamlet/config.json`; hooks read it via `find_server_url()`. No hardcoded port remains. See D-13.
- **Resolved in:** cycle 005

## Q-8: EVENT_SCHEMA has dead nested "data" block
- **Question:** `validation.py` EVENT_SCHEMA defines event-specific fields nested under a `"data"` sub-object that no real payload ever contains. The flat fields sent by hooks are not validated for type. Should the `"data"` block be removed and flat property entries added?
- **Source:** archive/cycles/004/code-quality.md (S2); archive/cycles/004/spec-adherence.md (D1, IC1); archive/cycles/004/gap-analysis.md (MI1)
- **Impact:** Schema documents the wrong contract. Event-specific fields are never type-validated. Future consumers reading the schema will attempt nested access and fail.
- **Status:** resolved
- **Resolution:** EVENT_SCHEMA rewritten with flat property entries; nested "data" block removed. All event-specific fields now validated against their actual wire format. See D-14.
- **Resolved in:** cycle 005

## Q-9: find_config() traversal collides with ~/.hamlet/config.json
- **Question:** `find_config()` traverses upward from cwd through all ancestors. `install_command` now writes `~/.hamlet/config.json` (containing `server_url` but not `project_id`). For most users, the home directory is an ancestor, so this file is always reached. `data.get("project_name", parent.name)` returns the home directory basename as project name for users without a per-project config.
- **Source:** archive/cycles/005/decision-log.md (D8, OQ2); archive/cycles/005/gap-analysis.md (MG1); archive/cycles/005/code-quality.md (M2)
- **Impact:** Wrong project name displayed in TUI for users without a per-project `.hamlet/config.json`. Project ID is still correct (cwd hash), so no data corruption.
- **Status:** resolved
- **Resolution:** Guard `if "project_id" not in data: continue` added in all four hook scripts. Configs without `project_id` are skipped during traversal. See D-17.
- **Resolved in:** cycle 006

## Q-10: tool_output schema rejects plain-string Bash responses
- **Question:** `EVENT_SCHEMA` constrains `tool_output` to `["object", "null"]`. Bash tool returns stdout as a plain string. Every Bash PostToolUse event with string output is silently discarded by schema validation. Should the schema type be widened to include `"string"`, or should `post_tool_use.py` wrap string responses in an object?
- **Source:** archive/cycles/005/decision-log.md (OQ6); archive/cycles/005/gap-analysis.md (MG2)
- **Impact:** Bash-heavy agents generate no world-state changes. Structures driven by Bash activity (forges) are never built from real tool activity.
- **Status:** open
- **Reexamination trigger:** Next validation or event processing work item.

## Q-11: notification_message extracted but never consumed downstream
- **Question:** `InternalEvent.notification_message` is populated by `event_processor.py` but `_handle_notification()` in `engine.py` is an explicit no-op placeholder. `WorldStateManager` builds event log entries as `"{hook_type}: {tool_name or ''}"`, so every Notification entry reads `"Notification: "` — message content is discarded. Should `_handle_notification()` be implemented and `WorldStateManager` updated to include the message?
- **Source:** archive/cycles/005/decision-log.md (OQ3, D6); archive/cycles/005/gap-analysis.md (SG1)
- **Impact:** Notification hook content never appears in the event log or TUI. The field being present in InternalEvent creates false confidence that it is used.
- **Status:** resolved
- **Resolution:** `_handle_notification()` logs `notification_message` when non-None. `handle_event()` builds summary as "Notification: {message}" via unconditional hook-type routing. See D-16.
- **Resolved in:** cycle 006

## Q-12: stop_reason extracted but never consumed downstream
- **Question:** `InternalEvent.stop_reason` is populated by `event_processor.py` but `_handle_stop()` in `engine.py` ignores it. All session stops are treated identically; the distinction between a clean stop (`"stop"`) and a mid-tool interruption (`"tool"`) is not captured.
- **Source:** archive/cycles/005/decision-log.md (OQ4, D6); archive/cycles/005/gap-analysis.md (SG2)
- **Impact:** Cannot differentiate session termination modes. Zombie detection and state transitions cannot use stop_reason to vary behavior.
- **Status:** resolved
- **Resolution:** `_handle_stop()` now logs `stop_reason` when non-None. Event log shows "Stop: {reason}". Behavioral differentiation remains deferred — see Q-13.
- **Resolved in:** cycle 006

## Q-13: stop_reason behavioral differentiation
- **Question:** Should "tool" (mid-tool interruption) and "stop" (clean termination) values of `stop_reason` produce different agent state transitions? Currently both receive identical treatment — zombie eviction handles stale pending_tools via TTL regardless of stop reason.
- **Source:** archive/cycles/006/decision-log.md (D-R3, OQ1); archive/cycles/006/gap-analysis.md (MG1)
- **Impact:** Interrupted sessions accumulate stale `pending_tools` entries until zombie TTL fires. Proactive cleanup on "tool" stop could reduce the delay.
- **Status:** open
- **Reexamination trigger:** Design decision on interrupted-session state semantics; zombie detection refinement work item.

## Q-14: handle_event() uses string comparison instead of enum identity for hook type dispatch
- **Question:** `manager.handle_event()` compares `event.hook_type.value == "Notification"` (string) rather than `event.hook_type == HookType.Notification` (enum identity). `engine.py` uses enum comparison. Should the dispatch idiom be unified?
- **Source:** archive/cycles/006/code-quality.md (M1); archive/cycles/006/decision-log.md (OQ3)
- **Impact:** If a `HookType` enum value is renamed, the Notification and Stop branches silently fall through to the else branch, producing wrong summaries. Two dispatch sites use divergent idioms.
- **Status:** open
- **Reexamination trigger:** Next event handling or manager.py work item.

## Q-15: Test coverage for 11 new HookType values and event pipeline branches
- **Question:** None of the 11 new `HookType` values added in WI-182 are covered by any test. The 11 new `handle_event()` branches in WI-183 are not exercised. The `on_resize` handler (WI-184) and `is_plugin_active()` (WI-185) are also untested. Should a focused test coverage cycle be prioritized?
- **Source:** archive/cycles/008/code-quality.md (S2), archive/cycles/008/gap-analysis.md (G2)
- **Impact:** Regressions in session/agent lifecycle tracking, structure work accumulation, viewport resize, and plugin detection will not be caught by the test suite. This is the primary risk carried forward from cycle 008.
- **Status:** open
- **Reexamination trigger:** Next test coverage or event handling work item.

## Q-16: notification_type field silently discarded
- **Question:** `notification.py` sends `notification_type` in params and `validation.py` declares it in the schema, but `InternalEvent` has no `notification_type` field and `event_processor.py` does not extract it. The value is silently discarded on every Notification event. Should the field be added to `InternalEvent` for downstream consumption?
- **Source:** archive/cycles/008/gap-analysis.md (G4), archive/cycles/008/code-quality.md (suggestions)
- **Impact:** Cannot differentiate notification types (progress vs. info vs. warning) in the TUI or event log. Pre-existing from cycle 005 but not previously tracked as a question.
- **Status:** open
- **Reexamination trigger:** Visual differentiation of notification types or next event processing work item.

## Q-17: is_plugin_active() uses substring match — false positive risk
- **Question:** `is_plugin_active()` uses `"hamlet" in key.lower()` to match plugin keys. A user with another plugin containing "hamlet" in its identifier would get a false positive, silently suppressing hook installation. Should the match be tightened to exact key or `installPath` check?
- **Source:** archive/cycles/008/gap-analysis.md (G3), archive/cycles/008/code-quality.md (suggestions)
- **Impact:** Minor — requires an unusual plugin name coincidence. The silent suppression (returns 0 with a warning) makes it visible but the heuristic is weak.
- **Status:** open
- **Reexamination trigger:** Plugin installation issues or next install.py work item.

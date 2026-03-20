# Change Plan — Refine-9: Quality Cycle (v0.4.x)

## What is changing and why

This cycle addresses quality, not features. Trigger: cycle 008 review passed but left a significant test-coverage gap (Q-15), several pre-existing open questions (Q-6, Q-10, Q-13, Q-14, Q-16), and structural code-health items identified by the architect survey.

**Three areas:**

1. **Test coverage** — 11 new HookType values, 11 new handle_event branches, on_resize, is_plugin_active, and all 15 hook scripts have zero test coverage. Adding tests for all of these.

2. **Documentation** — No CLAUDE.md exists. README/QUICKSTART are stale (4 hooks shown, manual JSON config, missing commands). Public API docstrings are sparse on the 5 core modules.

3. **Code health and functional gaps** — Enum identity convention comment in handle_event; orphaned saver.py removal; startup sequence deduplication; /hamlet/health test; Bash tool_output schema widening (Q-10); notification_type extraction (Q-16); stop_reason behavioral differentiation using available telemetry (Q-13); Protocol interfaces replacing Any-typed module boundaries.

## Scope boundary

**Changing**: tests, CLAUDE.md, README, QUICKSTART, docstrings, enum convention comment, saver.py deletion, app_factory.py extraction, validation.py, internal_event.py, event_processor.py (schema + notification_type), inference/engine.py (stop_reason), world_state/manager.py (stop_reason), protocols.py (new).

**Not changing**: game mechanics, simulation logic, TUI layout, hook scripts, hooks.json, persistence schema, world state data model structure, CLI commands, MCP server logic (beyond health endpoint test), agent inference rules.

## Expected impact

- Test suite coverage increases significantly for the event pipeline and hook scripts
- Regressions in v0.4.0 functionality will now be caught automatically
- Bash-heavy agent sessions will generate world-state changes (Q-10 fix)
- Agents interrupted mid-tool are properly marked IDLE rather than waiting for zombie TTL (Q-13 fix)
- Notification type differentiation available for downstream use (Q-16 fix)
- Module boundaries are statically typed — mypy/pyright can catch interface mismatches
- Startup code is in one place (app_factory.py)
- Developer onboarding is faster (CLAUDE.md)

## Work items

WI-187 through WI-198 (12 items)

## What Is Changing

### 1. All Claude Code Hook Types (WI-179–181)
Claude Code now exposes 26+ hook event types. Hamlet currently implements 4 (PreToolUse, PostToolUse, Notification, Stop). This cycle adds the remaining relevant hooks:

**Agent/session lifecycle** — SubagentStart, SubagentStop, SessionStart, SessionEnd, TeammateIdle, TaskCompleted
**System/observation** — PostToolUseFailure, UserPromptSubmit, PreCompact, PostCompact, StopFailure

All new hooks are Python scripts following the existing pattern: read stdin, find_config(), POST to daemon, exit. All use `async: true` where supported.

**Fix**: Remove `async: true` from PreToolUse — per Claude Code docs, `async` is unsupported on blocking hook events. This is also the likely cause of the persistent "1 error during load" in plugin reload.

### 2. Event Schema for New Hook Types (WI-182)
HookType enum, InternalEvent typed fields, and validation schema extended to cover all 11 new hook event names and their stdin payloads.

### 3. Daemon Handling for New Event Types (WI-183)
EventProcessor and WorldStateManager extended to accept and route new event types. Each new event type triggers at minimum a random agent movement or animation tick — the goal is visual activity, not semantic precision. New types map to existing animation/movement infrastructure.

### 4. Adaptive Viewport (WI-184)
WorldView widget wired to update ViewportManager on mount and on Textual resize events. Uses `self.size` (the actual Textual widget dimensions) rather than any hardcoded values. ViewportManager.resize() already exists but was never called.

### 5. Plugin Update Hygiene (WI-185)
`hamlet install` detects whether the hamlet plugin is currently active (hooks registered via plugin's hooks.json) and skips installation with a clear warning. Prevents double-firing of hooks when both `hamlet install` and the plugin are active.

### 6. Version Bump to 0.4.0 (WI-186)
All four version locations updated: pyproject.toml, .claude-plugin/plugin.json, src/hamlet/__init__.py, src/hamlet/cli/__init__.py.

## Scope Boundary

**Not changing**: inference engine logic, TUI layout/widgets (except WorldView resize wiring), persistence schema, mcp/server.py, existing hook scripts (hamlet_hook_utils.py, pre_tool_use.py, post_tool_use.py, notification.py, stop.py), world state data model, simulation engine.

## Expected Impact

After this cycle:
- All 15 hook types fire and reach the daemon; busy sessions produce more events → more visual activity
- Viewport correctly fills the terminal window and adapts on resize
- Plugin updates via marketplace pick up new hook registrations automatically
- `hamlet install` and plugin coexist safely without duplicate hooks
- Load error from `async: true` on PreToolUse is resolved

## New Work Items
WI-179 through WI-186 (8 items)

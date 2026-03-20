# Execution Strategy — Refine-9: Quality Cycle

## Mode
Batched parallel

## Parallelism
4 concurrent workers per group

## Worktrees
Disabled (no conflicting file scopes within groups)

## Review cadence
Incremental review after each work item completes.

## Agent model
sonnet (default)

## Work Item Groups

### Group 1 — Parallel (no dependencies, no overlapping file scope)

| WI | Title | Files touched |
|----|-------|---------------|
| 187 | Event pipeline tests | tests/test_event_processor.py, tests/test_world_state_manager.py |
| 188 | on_resize + is_plugin_active tests | tests/test_tui_world_view.py, tests/test_cli_install.py |
| 189 | Hook script unit tests | tests/test_hooks.py |
| 190 | CLAUDE.md | CLAUDE.md |
| 191 | README + QUICKSTART update | README.md, QUICKSTART.md |
| 192 | Public API docstrings | src/.../manager.py, inference/engine.py, event_processor.py, server.py, facade.py |
| 194 | Remove saver.py + deduplicate startup | persistence/saver.py, app_factory.py, __main__.py, daemon.py |
| 195 | Health endpoint test | tests/test_mcp_server.py |

Run 4 at a time: first batch [187, 188, 189, 190], second batch [191, 192, 194, 195].

Note: WI-192 touches src files that WI-193, 197, and 198 also touch. It must complete before group 2 starts.

### Group 2 — Parallel (depends on group 1 items)

| WI | Title | Depends on | Files touched |
|----|-------|-----------|---------------|
| 193 | Enum identity comment | 192 | src/hamlet/world_state/manager.py |
| 196 | tool_output schema + notification_type | 187, 192 | validation.py, internal_event.py, event_processor.py, tests/test_event_processor.py |

Run both in parallel (non-overlapping file scope).

### Group 3 — Sequential

| WI | Title | Depends on | Files touched |
|----|-------|-----------|---------------|
| 197 | stop_reason differentiation | 192, 193, 196 | inference/engine.py, world_state/manager.py, tests/test_inference_engine.py |

### Group 4 — Sequential

| WI | Title | Depends on | Files touched |
|----|-------|-----------|---------------|
| 198 | Protocol interfaces | 192, 197 | protocols.py, simulation/engine.py, server.py, event_processor.py, inference/engine.py, manager.py |

## Dependency Graph

```
187 ─────────────────────────────────────► 196
188 (independent)
189 (independent)
190 (independent)
191 (independent)
192 ──────────────────► 193 ──────────────► 197 ──► 198
192 ─────────────────────────────────────► 196 ──► 197
192 ────────────────────────────────────────────────► 198
194 (independent)
195 (independent)
```

## Total work items: 12 (WI-187 through WI-198)

## Parallelism
Max concurrent agents: 6

## Worktrees
Enabled: no
Reason: File scopes are largely non-overlapping. Items that share adjacency (WI-179/180 and hooks.json) are sequenced rather than concurrent.

## Review Cadence
Incremental review after each item completes. Comprehensive review after all items.

## Work Item Groups

### Group 1 — Parallel (no dependencies)

| ID  | Title                                              | Complexity | Key Files                                                     |
|-----|----------------------------------------------------|------------|---------------------------------------------------------------|
| 179 | Agent/session lifecycle hook scripts               | medium     | hooks/session_start.py, session_end.py, subagent_start.py, subagent_stop.py, teammate_idle.py, task_completed.py (create) |
| 180 | System/observation hook scripts                    | medium     | hooks/post_tool_use_failure.py, user_prompt_submit.py, pre_compact.py, post_compact.py, stop_failure.py (create) |
| 182 | Extend event schema and HookType enum              | medium     | src/hamlet/events/schema.py, src/hamlet/events/types.py (modify) |
| 184 | Adaptive viewport wiring                           | low        | src/hamlet/tui/world_view.py (modify)                         |
| 185 | hamlet install plugin detection                    | low        | src/hamlet/cli/__init__.py (modify)                           |
| 186 | Version bump to 0.4.0                              | low        | pyproject.toml, .claude-plugin/plugin.json, src/hamlet/__init__.py, src/hamlet/cli/__init__.py (modify) |

### Group 2 — After Group 1

| ID  | Title                                              | Complexity | Key Files                                       | Depends On    |
|-----|----------------------------------------------------|------------|-------------------------------------------------|---------------|
| 181 | Update hooks.json with all 15 hooks                | low        | hooks/hooks.json (modify)                       | WI-179, WI-180 |
| 183 | Daemon handling for new event types                | medium     | src/hamlet/events/processor.py, src/hamlet/world/state.py (modify) | WI-182 |

## Dependency Graph

```
179 ──┐
      ├──► 181
180 ──┘

182 ──► 183

184 ─── (independent)
185 ─── (independent)
186 ─── (independent)
```

## Agent Configuration
Model for workers: sonnet
Model for reviewers: sonnet
Permission mode: acceptEdits

# Review Manifest — Cycle 008

## Work Items

| # | Title | File Scope | Incremental Verdict | Findings (C/S/M) | Work Item | Review Path |
|---|---|---|---|---|---|---|
| 179 | New hook scripts — agent/session lifecycle | hooks/session_start.py, session_end.py, subagent_start.py, subagent_stop.py, teammate_idle.py, task_completed.py | Pass | 0/0/0 | work-items.yaml#179 | archive/incremental/179-lifecycle-hooks-final.md |
| 180 | New hook scripts — system/observation events | hooks/post_tool_use_failure.py, user_prompt_submit.py, pre_compact.py, post_compact.py, stop_failure.py | Pass | 0/0/2 | work-items.yaml#180 | archive/incremental/180-system-hooks-rework.md |
| 181 | Update hooks.json — 15 hooks, fix PreToolUse async | hooks/hooks.json | Pass | 0/0/0 | work-items.yaml#181 | archive/incremental/181-hooks-json.md |
| 182 | Extend event schema for new hook types | src/hamlet/event_processing/internal_event.py, src/hamlet/mcp_server/validation.py, src/hamlet/event_processing/event_processor.py | Pass | 0/0/3 | work-items.yaml#182 | archive/incremental/182-event-schema.md |
| 183 | Daemon handling for new event types with visual triggers | src/hamlet/world_state/manager.py | Pass | 0/0/1 | work-items.yaml#183 | archive/incremental/183-daemon-handling-final2.md |
| 184 | Adaptive viewport — wire WorldView to terminal size | src/hamlet/tui/world_view.py | Pass | 0/0/0 | work-items.yaml#184 | archive/incremental/184-adaptive-viewport.md |
| 185 | Plugin update hygiene — hamlet install detects plugin | src/hamlet/cli/commands/install.py | Pass | 0/0/1 | work-items.yaml#185 | archive/incremental/185-install-hygiene.md |
| 186 | Version bump to 0.4.0 | pyproject.toml, .claude-plugin/plugin.json, src/hamlet/__init__.py, src/hamlet/cli/__init__.py | Pass | 0/0/0 | work-items.yaml#186 | archive/incremental/186-version-bump.md |

## Notes
- All 8 work items passed incremental review. WI-179 and WI-183 required two rework cycles each before passing.
- Minor findings: test coverage gaps (WI-182 — new HookType values untested), undocumented dual-format JSON parsing in is_plugin_active (WI-185), infallible literal assignments in try/except blocks (WI-183).
- Cycle 008 is a capstone review of the v0.4.0 refinement (refine-7): full hook coverage, adaptive viewport, plugin install hygiene.

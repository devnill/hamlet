## Verdict: Fail

Five of the eleven new hook scripts violate P-6 by omitting `os.chdir(cwd)`, causing config traversal to start from the wrong directory; this produces silent project-identity mismatches in multi-project setups.

---

## Critical Findings

None.

---

## Significant Findings

### S1: WI-180 hooks omit `os.chdir(cwd)` — wrong project identity under P-6

- **Files**:
  - `hooks/post_tool_use_failure.py` (entire `main()`)
  - `hooks/user_prompt_submit.py` (entire `main()`)
  - `hooks/pre_compact.py` (entire `main()`)
  - `hooks/post_compact.py` (entire `main()`)
  - `hooks/stop_failure.py` (entire `main()`)

- **Issue**: The six WI-179 hooks (`session_start.py`, `session_end.py`, `subagent_start.py`, `subagent_stop.py`, `teammate_idle.py`, `task_completed.py`) all read `hook_input.get("cwd", "")` from stdin and call `os.chdir(cwd)` before invoking `find_server_url()` and `find_config()`. The five WI-180 hooks do none of this. Both `find_server_url()` and `find_config()` in `hamlet_hook_utils.py` begin traversal from `Path(os.getcwd())` (lines 31 and 55). Without `os.chdir()`, these hooks traverse from the process's launch directory — which is controlled by Claude Code, not the project — so they may resolve a different project's config or fall back to the global default, producing wrong `project_id` and `project_name` values. Policy P-6 requires config traversal for project identity; P-9 requires reading `server_url` from config. Both are undermined for the WI-180 group.

- **Impact**: In a multi-project or non-standard launch-directory environment, `PostToolUseFailure`, `UserPromptSubmit`, `PreCompact`, `PostCompact`, and `StopFailure` events are attributed to the wrong project. Because the hooks catch all exceptions silently (GP-7), this failure is invisible.

- **Suggested fix**: Apply the same `cwd`-chdir pattern used in all WI-179 hooks immediately after reading stdin:
  ```python
  hook_input = json.load(sys.stdin)
  cwd = hook_input.get("cwd", "")
  if cwd and os.path.isdir(cwd):
      os.chdir(cwd)
  ```
  Also add `import os` to each of the five files.

---

### S2: No tests for any new HookType values or new `handle_event` branches

- **Files**:
  - `tests/test_event_processor.py` — no test uses any of the 11 new `HookType` values
  - `tests/test_world_state_manager.py` — no test exercises any new `handle_event` branch
  - `tests/test_tui_world_view.py` — no test for `on_mount` viewport resize call or `on_resize` handler

- **Issue**: The review manifest (line 18) noted this gap for WI-182 and flagged it as minor. At the capstone level, the impact is larger. The 11 new `HookType` values added in WI-182 are never used in any test. The 11 new branches in `handle_event()` added in WI-183 are never exercised. Specifically:
  - `HookType.SessionStart` branch calls `get_or_create_project` and `get_or_create_session` — not tested.
  - `HookType.SessionEnd` branch sets `AgentState.IDLE` under `self._lock` — not tested.
  - `HookType.SubagentStart` branch calls `get_or_create_agent` — not tested.
  - `HookType.TaskCompleted` branch calls `add_work_units` with a randomly chosen `StructureType` — not tested.
  - `on_mount` viewport resize call and `on_resize` Textual handler added in WI-184 — not tested.
  - `is_plugin_active()` added in WI-185 — not tested.

- **Impact**: Regressions in the most important new behaviors (session and agent lifecycle, structure work accumulation, resize wiring, plugin detection) will not be caught by the test suite.

- **Suggested fix**: Add test cases covering at minimum: each new `HookType` round-trips through `process_event`; `handle_event` for `SessionStart`, `SessionEnd`, `SubagentStart`, `TaskCompleted` produce the expected state mutations; `on_resize` forwards dimensions to `viewport.resize`; `is_plugin_active` returns correct values for both JSON formats.

---

## Minor Findings

### M1: `stop_failure.py` sends nested `error` object — borderline P-8

- **File**: `hooks/stop_failure.py:29–32`

- **Issue**: The `params` dict contains `"error": {"type": ..., "reason": ...}` — a nested sub-object. Policy P-8 specifies "flat params format (no nested 'data' sub-object)". The schema in `validation.py:49` explicitly permits `"error": {"type": ["object", "null"]}` and `InternalEvent` stores it as `dict[str, Any] | None`, so the pipeline accepts it. However, this is the only hook that sends a nested value other than `tool_input`/`tool_output`. If the policy intent covers all nested structures, this is a violation; at minimum it is undocumented asymmetry.

- **Suggested fix**: Either flatten the error into `error_type` and `error_reason` top-level params and update the schema and `InternalEvent` accordingly, or add an explicit comment citing why nested `error` is permitted as an exception to P-8.

### M2: Infallible literal assignments wrapped in `try/except` — WI-183

- **File**: `src/hamlet/world_state/manager.py:762–829`

- **Issue**: Several `handle_event` branches wrap a plain string assignment in `try/except Exception`:
  ```python
  elif event.hook_type == HookType.SubagentStop:
      try:
          summary = f"SubagentStop: {event.agent_type or 'unknown'}"
      except Exception as exc:
          logger.warning("SubagentStop handler error: %s", exc)
          summary = "SubagentStop"
  ```
  The same pattern appears for `TeammateIdle`, `PostToolUseFailure`, `UserPromptSubmit`, `PreCompact`, `PostCompact`, and `StopFailure`. A bare f-string on a known-`str | None` field cannot raise. The `try` block obscures the fact that no real error is possible and makes the code harder to read. This was noted in the incremental review manifest (line 18) but was not corrected.

- **Suggested fix**: Remove the `try/except` wrappers from branches that contain only the `summary = f"..."` assignment. Reserve `try/except` for branches that call async helpers or mutate state, as the `SessionStart`, `SessionEnd`, `SubagentStart`, and `TaskCompleted` branches correctly do.

### M3: `UserPromptSubmit` hook does not read `cwd` even though prompt hook fires in project context

- **File**: `hooks/user_prompt_submit.py` (same root as S1, but separately notable)

- **Issue**: The `UserPromptSubmit` hook is the most likely hook to fire from within a user's active project session, making correct `project_id` resolution particularly valuable. This amplifies the impact of the S1 finding for this specific hook.

- **Suggested fix**: Addressed by the S1 fix.

### M4: `HOOK_SCRIPTS` in `install.py` still lists only 4 hooks — not updated for v0.4.0

- **File**: `src/hamlet/cli/commands/install.py:20–25`

- **Issue**: The `HOOK_SCRIPTS` dict maps only `PreToolUse`, `PostToolUse`, `Notification`, and `Stop`. The `hooks.json` registered in WI-181 covers 15 hook types. The `install` command is for non-plugin installations (settings.json injection). When a user runs `hamlet install`, they get only 4 of 15 hooks configured — the remaining 11 new hooks are never registered. The `remove_hooks_from_settings` and `uninstall_command` functions share the same incomplete list, so they also fail to clean up any hooks that were installed by other means. This predates this cycle but the cycle added 11 hooks without updating this list.

- **Impact**: Non-plugin users who run `hamlet install` get no coverage of `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `TeammateIdle`, `TaskCompleted`, `PostToolUseFailure`, `UserPromptSubmit`, `PreCompact`, `PostCompact`, `StopFailure`. These users get a degraded experience with no error or warning.

- **Suggested fix**: Add all 11 new hook types and their script filenames to the `HOOK_SCRIPTS` dict in `install.py`, matching the entries in `hooks.json`.

---

## Suggestions

- **Cross-hook test fixture**: A parametrized test over all 15 `HookType` values for `process_event` would catch future schema/enum divergence automatically and costs minimal effort.
- **`is_plugin_active` edge case**: The function uses `"hamlet" in key.lower()` to match plugin keys. If a user has any other plugin with "hamlet" in its name or path, this returns a false positive and suppresses hook installation silently. A stricter match (e.g., exact key `"hamlet"` or checking `installPath` contains `/hamlet/`) would be more robust.
- **`notification_type` field**: `notification.py` sends `notification_type` in params; `validation.py` declares it in the schema; but `InternalEvent` has no `notification_type` field and `event_processor.py` does not extract it. The value is silently discarded. This is pre-existing but worth tracking.

---

## Unmet Acceptance Criteria

No individual work item spec documents were provided for detailed AC cross-check. Based on the WI descriptions in the review manifest and the code examined:

- [ ] **WI-180 (P-5/P-6 compliance)**: Hook scripts must read event data from stdin and use `find_config()` traversal for project identity. Five of the five WI-180 hooks do not perform `os.chdir(cwd)` before traversal, violating P-6 in multi-project setups. (See S1.)
- [ ] **WI-185 (full hook coverage in install)**: If WI-185's scope included keeping `install.py` consistent with the new hooks, `HOOK_SCRIPTS` is not updated. (See M4.)

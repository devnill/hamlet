## Verdict: Fail

The implementation satisfies most acceptance criteria but has a silent data corruption bug in `find_config()` and dead code across all four files.

## Critical Findings

### C1: `find_config()` returns empty string `project_id` when config exists but lacks the key
- **File**: `hooks/pre_tool_use.py:41`, `hooks/post_tool_use.py:41`, `hooks/notification.py:37`, `hooks/stop.py:37`
- **Issue**: When a `.hamlet/config.json` file is found but does not contain a `project_id` key, `cfg.get("project_id", "")` returns `""`. Execution then returns `("", ...)` immediately — the fallback hash path is never reached. An empty string `project_id` is sent to the server for every event from that project.
- **Impact**: All events from a project with a malformed or incomplete config (missing `project_id`) are bucketed under `project_id = ""`. Multiple unrelated projects with partial configs share one village. The hash fallback mandated by criterion 4 is bypassed entirely.
- **Suggested fix**: After reading the config, check whether the returned `project_id` is non-empty before returning. If it is empty, fall through to the hash fallback:
  ```python
  cfg = json.loads(config_path.read_text())
  pid = cfg.get("project_id", "")
  if pid:
      return pid, cfg.get("project_name", directory.name)
  ```

## Significant Findings

None.

## Minor Findings

### M1: `_cwd_hash()` is dead code in all four hook files
- **File**: `hooks/pre_tool_use.py:15-16`, `hooks/post_tool_use.py:15-16`, `hooks/notification.py:11-12`, `hooks/stop.py:11-12`
- **Issue**: `_cwd_hash()` is defined but never called. The hash computation inside `find_config()` is written inline.
- **Suggested fix**: Remove `_cwd_hash()` from all four files, or replace the inline hash in `find_config()` with a call to it.

### M2: No tests for any hook script
- **File**: `tests/` (no test files for hooks)
- **Issue**: No unit tests covering `find_config()`, stdin parsing logic, payload construction, or error logging path. The C1 bug would be caught immediately by a test that creates a config file with no `project_id` key.
- **Suggested fix**: Add tests using `tmp_path` to verify: (a) `find_config()` returns hash-based `project_id` when config exists but has no `project_id`; (b) traversal reaches a parent directory; (c) fallback triggers when no config exists.

## Unmet Acceptance Criteria

- [ ] **Criterion 4** — "If no config found, `project_id` defaults to a deterministic hash" — The hash fallback is bypassed when a config exists but has no `project_id` key, returning `""` instead.

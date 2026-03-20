## Verdict: Fail

All 6 scripts are structurally correct and most acceptance criteria are met, but `find_config()` ignores the `cwd` field from stdin, meaning every script resolves the project config relative to the hook binary's working directory rather than the Claude Code session's working directory.

## Critical Findings

### C1: `cwd` from stdin is ignored — project config resolved from wrong directory

- **File**: `/Users/dan/code/hamlet/hooks/session_start.py:18`, `/Users/dan/code/hamlet/hooks/session_end.py:18`, `/Users/dan/code/hamlet/hooks/subagent_start.py:18`, `/Users/dan/code/hamlet/hooks/subagent_stop.py:18`, `/Users/dan/code/hamlet/hooks/teammate_idle.py:18`, `/Users/dan/code/hamlet/hooks/task_completed.py:18`
- **Issue**: The WI-179 notes explicitly state that each hook's stdin payload includes a `cwd` field representing the Claude Code session's working directory, and that `find_config()` must use it: *"find_config() uses cwd — pass hook_input.get("cwd") or os.getcwd()"*. None of the 6 scripts read `hook_input.get("cwd")`. All 6 call `find_config()` with no argument, causing `hamlet_hook_utils.find_config()` to fall back to `os.getcwd()`, which is the process working directory of the hook script itself, not the session's project directory. When a hook is registered globally (e.g., `~/.claude/hooks/`), the script's cwd is unlikely to be the project root, so `.hamlet/config.json` will not be found and all events will be tagged with a synthetic project ID derived from a hash of the wrong path.
- **Impact**: Every event from these 6 hooks will have an incorrect `project_id` and `project_name` in its payload. The server will create phantom projects and fail to associate lifecycle events with the correct village.
- **Suggested fix**: Read the cwd from stdin and `os.chdir` before calling `find_config()`, or pass it through. The simplest conforming fix:
  ```python
  hook_input = json.load(sys.stdin)
  cwd = hook_input.get("cwd", "")
  if cwd:
      os.chdir(cwd)
  project_id, project_name = find_config()
  ```
  This matches the pattern described in the notes and matches how any future callers of `find_config()` would expect it to behave.

## Significant Findings

None.

## Minor Findings

### M1: `os` module not imported in any of the 6 scripts

- **File**: `/Users/dan/code/hamlet/hooks/session_start.py:3-7` (same in all 6)
- **Issue**: If the fix for C1 is applied using `os.chdir()`, the `os` module must be imported. It is currently absent from all 6 files. The reference pattern `notification.py` also omits `os`, but `notification.py` does not need the `cwd` field.
- **Suggested fix**: Add `import os` alongside the other stdlib imports when applying the C1 fix.

### M2: `find_server_url()` also ignores `cwd`

- **File**: `/Users/dan/code/hamlet/hooks/session_start.py:16` (same in all 6)
- **Issue**: `find_server_url()` in `hamlet_hook_utils` traverses from `os.getcwd()` upward looking for a project-level `server_url` override. Because the scripts do not `os.chdir(cwd)` before calling `find_server_url()`, the same wrong-cwd problem applies to server URL resolution. If the fix for C1 is applied with `os.chdir()` before both utility calls (as shown), this is resolved automatically. If a non-chdir approach is chosen for `find_config()`, `find_server_url()` needs a parallel fix.
- **Suggested fix**: Apply the `os.chdir(cwd)` fix before both `find_server_url()` and `find_config()` calls, so both utilities operate in the correct directory context.

## Unmet Acceptance Criteria

- [ ] **Criterion 8** — "All 6 scripts call find_config() and find_server_url(), exit 0 in finally block." The calls are present, but `find_config()` is not called correctly per the implementation spec: the WI-179 notes require passing or establishing `cwd` from stdin before the call. The utility's contract depends on the process working directory being the project root; none of the scripts set this up. The criterion is therefore not satisfied in substance even though the call sites exist.

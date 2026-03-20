# Code Quality Report — Hamlet Cycle 002 (Plugin Execution & server_url Plumbing)

## Verdict: Pass

The three-tier `find_server_url()` implementation is correct and consistent across all four hooks; `mcp/start.sh` is valid POSIX sh; no critical or significant defects were found.

## Critical Findings

None.

## Significant Findings

None.

## Minor Findings

### M1: No exception handling on existing-config read in `hamlet_init`
- **File**: `/Users/dan/code/hamlet/mcp/server.py:42`
- **Issue**: `json.loads(config_path.read_text())` is called with no try/except. If `.hamlet/config.json` exists but contains invalid JSON (truncated write, manual edit error), `call_tool` raises an unhandled exception rather than returning a user-readable error message.
- **Suggested fix**: Wrap lines 42–46 in a try/except and return a `TextContent` error message, consistent with the graceful-degradation principle (P7).

### M2: `find_server_url()` and `find_config()` duplicated verbatim across four hook files
- **File**: `/Users/dan/code/hamlet/hooks/pre_tool_use.py:19–61`, `/Users/dan/code/hamlet/hooks/post_tool_use.py:19–61`, `/Users/dan/code/hamlet/hooks/notification.py:15–57`, `/Users/dan/code/hamlet/hooks/stop.py:15–57`
- **Issue**: Both functions are copy-pasted in full into every hook module. A bug fix or behaviour change must be applied in four places.
- **Suggested fix**: Extract `find_server_url()`, `find_config()`, `_cwd_hash()`, and `_log_error()` into a shared `hooks/common.py` and import from there.

### M3: `import os` inside function bodies
- **File**: `/Users/dan/code/hamlet/hooks/pre_tool_use.py:21`, `49`; same pattern in all four hook files
- **Issue**: `import os` is placed inside `find_server_url()` and `find_config()` rather than at module level. `os` is part of the standard library and is always available; there is no reason to defer its import.
- **Suggested fix**: Move `import os` to the top-level import block in each hook file.

## Unmet Acceptance Criteria

None.

## Summary

Cycle 007 introduced `hamlet_hook_utils.py` and minor changes to `mcp/start.sh` and `mcp/server.py`. One significant pre-existing gap is now visible: `find_config()` silently falls through to a hash-based phantom `project_id` when `.hamlet/config.json` contains malformed JSON, routing all hook events to a new ghost village with no diagnostic trail. Two integration gaps exist around missing test coverage for the `hamlet_init` MCP tool. Two minor edge cases are noted.

## Integration Gaps

### II1: `hamlet_init` MCP tool has no test coverage
- **Missing**: Tests for `mcp/server.py`'s `call_tool()` and `list_tools()` handlers
- **Impact**: The `hamlet_init` implementation — including the config-already-exists guard, directory creation, UUID generation, and the new `server_url` parameter — has no test coverage. `test_cli_init.py` covers the separate CLI `hamlet init` path, not the MCP tool.
- **Suggested addition**: `tests/test_mcp_plugin_server.py` testing: (1) new config with no server_url writes default, (2) new config with custom server_url writes it, (3) existing config returns early without overwriting.

### II2: No test for `server_url` parameter path
- **Missing**: Regression guard for the new `arguments.get("server_url") or default_server_url` logic
- **Impact**: A future change could silently break the parameter without test failure.
- **Suggested addition**: Part of II1 — include the three `server_url` scenarios in the MCP server test file.

## Missing Requirements

None.

## Edge Cases Not Handled

### EC1: `find_server_url()` silently ignores malformed project config
- **Component**: `/Users/dan/code/hamlet/hooks/hamlet_hook_utils.py:22-28`
- **Scenario**: `.hamlet/config.json` exists but contains invalid JSON. The `except Exception: pass` silently falls through to global config or default URL.
- **Impact**: Minor — user's project config is ignored silently; hook fires against wrong server. Hard to diagnose.
- **Suggested fix**: Call `_log_error("find_server_url", exc)` inside the `except` block before `pass`.

### EC2: `find_config()` falls through to phantom `project_id` when config JSON is malformed
- **Component**: `/Users/dan/code/hamlet/hooks/hamlet_hook_utils.py:46-52`
- **Scenario**: `.hamlet/config.json` exists but cannot be parsed. Function skips it and returns `project-{hash}` fallback.
- **Impact**: Significant — phantom `project_id` causes hook events to create a new ghost village in the database. User's real village stops receiving events. Data diverges silently.
- **Suggested fix**: Call `_log_error("find_config", exc)` inside the `except` block before `pass`.

### EC3: `sys.path.insert` may fail when hooks directory is symlinked
- **Component**: All four hook scripts, `sys.path.insert(0, str(Path(__file__).parent))`
- **Scenario**: If `hooks/` is symlinked, `Path(__file__).parent` may not resolve to the directory containing `hamlet_hook_utils.py`.
- **Impact**: Minor — `ImportError` caught by outer `except Exception`, hook fires without sending event (consistent with GP-7).
- **Suggested fix**: Use `Path(__file__).resolve().parent` instead of `Path(__file__).parent`.

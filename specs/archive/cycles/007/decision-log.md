# Decision Log — Cycle 007

## What Was Built

Cycle 007 executed four independent work items (WI-174 through WI-177) from refine-6. All passed incremental reviews on first attempt with no critical or significant findings.

**WI-174**: Extracted `_cwd_hash`, `find_server_url`, `find_config`, `_log_error` from all four hook scripts into `hooks/hamlet_hook_utils.py`. Each hook imports via `sys.path.insert(0, str(Path(__file__).parent))`. ~200 lines of duplicated code removed.

**WI-175**: Deleted `pre_tool_use.sh`, `post_tool_use.sh`, `notification.sh`, `stop.sh` — none referenced by any active config.

**WI-176**: Changed `mcp/start.sh` import check from `import mcp` to `from mcp.server import Server`.

**WI-177**: Added optional `server_url` parameter to `hamlet_init` in `mcp/server.py`. Written to `.hamlet/config.json` at init time; defaults to `http://localhost:8080/hamlet/event`.

## Key Decisions

### D1: sys.path.insert for intra-hooks imports
Hook scripts add hooks directory to sys.path at runtime. No package install required — hooks are runnable standalone by Claude Code per GP-2.

### D2: Retain _log_error as private name
Carried from per-script implementations. Code reviewer flagged this (M2): all four hooks import a private-prefixed name across module boundary. Deferred.

### D3: server_url parameter is optional, defaults gracefully
Omitting server_url in hamlet_init uses default URL. Zero extra configuration for standard deployments (GP-11).

## Review Findings Summary

All three comprehensive reviewers returned **Pass**. No critical or significant findings from code-quality or spec-adherence reviews.

**Code quality**: 4 minor findings — timing key collision under concurrent invocations (M1), `_log_error` private name imported across module boundary (M2), hamlet_init filesystem errors not surfaced as readable TextContent (M3), datetime module-level import in hamlet_hook_utils.py used only in _log_error (M4).

**Spec adherence**: Pass, Principle Violations: None. All applicable guiding principles satisfied.

**Gap analysis**: EC2 (significant) — `find_config()` silently falls through to phantom `project_id` on malformed `.hamlet/config.json`, causing hook events to route to a ghost village with no diagnostic trail. Also: II1/II2 (no test coverage for hamlet_init MCP path), EC1 (find_server_url silent pass on malformed config), EC3 (sys.path.insert may fail on symlinked hooks dir, minor).

## Open Questions

1. **OQ2**: Should `find_config()` and `find_server_url()` call `_log_error` on malformed JSON? EC2 (significant) says yes — one-line fix.
2. **OQ4**: Should `hamlet_init` MCP tool have test coverage? II1/II2 flags zero coverage for call_tool() path.
3. **OQ1**: Should `_log_error` be renamed to a public name? M2.
4. **OQ3**: Should hamlet_init directory/write errors return readable TextContent? M3.
5. **OQ5**: Should sys.path.insert use `.resolve().parent`? EC3 (minor).

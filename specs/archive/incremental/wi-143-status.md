# WI-143 Status — Fix mcp/start.sh path resolution

**Status:** Complete

## Change Made

Replaced `SCRIPT_DIR="${CLAUDE_PLUGIN_ROOT}/mcp"` with self-locating logic in `/Users/dan/code/hamlet/mcp/start.sh`.

## Acceptance Criteria

- Script derives its own directory via `BASH_SOURCE[0]` — satisfied
- Works when `CLAUDE_PLUGIN_ROOT` is not set — satisfied (no longer referenced)
- uv path and python3 fallback both use `SCRIPT_DIR` — satisfied

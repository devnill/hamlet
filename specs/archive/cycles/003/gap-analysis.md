# Gap Analysis — Cycle 3 (WI-171)

## Verdict: Fail

SG1 is fully addressed. One new significant gap identified: `python3` not on PATH produces a misleading diagnostic.

## Critical Gaps

None.

## Significant Gaps

### SG1-new: `python3` not on PATH produces misleading "mcp package not found" error
- **File**: `/Users/dan/code/hamlet/mcp/start.sh:7`
- **Gap**: The `else` branch assumes `python3` is available. There is no `command -v python3` guard analogous to the `command -v uv` guard on line 3. When `python3` is absent, `python3 -c "import mcp"` exits non-zero, causing the `if !` branch to fire and emit "hamlet: mcp package not found. Install uv or run: pip install mcp" — which is factually wrong. The user is told to install mcp when the actual problem is that python3 is not installed.
- **Impact**: Users without uv and without python3 on PATH receive a misleading diagnostic. P11 (low-friction setup) is violated at the exact failure point WI-171 was meant to improve.

## Minor Gaps

### MG1: Dead `.sh` wrapper files never referenced by hooks.json
- **Files**: `hooks/pre_tool_use.sh`, `hooks/post_tool_use.sh`, `hooks/notification.sh`, `hooks/stop.sh`
- **Gap**: `hooks.json` references `.py` scripts directly. Four `.sh` wrapper files exist that are never called.
- **Recommendation**: Defer — no runtime impact.

### MG2: `hamlet_init` success message references non-existent `hamlet` CLI commands
- **File**: `/Users/dan/code/hamlet/mcp/server.py:61-63`
- **Gap**: Next-steps text instructs user to run `hamlet daemon` and `hamlet`. No such CLI entry points exist.
- **Recommendation**: Defer — CLI work is out of scope for this session.

## Previously Open Gap: Resolved

SG1 (prior): MCP server silently fails when uv absent and mcp not pre-installed — **Fixed by WI-171**.

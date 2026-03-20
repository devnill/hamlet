# Gap Analysis — Cycle 4 (WI-172)

## Verdict: Fail

WI-172 is fully addressed. Two significant gaps remain in the plugin delivery chain.

Note: Hook scripts already have execute permission (verified: `-rwxr-xr-x`). Gap analyst EC1/IR1 is not applicable.

## Critical Gaps

None.

## Significant Gaps

### SG1: `hamlet_init` tool output does not mention `server_url` — user cannot discover how to customize port
- **File**: `/Users/dan/code/hamlet/mcp/server.py`
- **Gap**: `hamlet_init` writes a `server_url` field to `.hamlet/config.json` but the tool description and success output do not mention this field. A user who needs hamlet on a different port (e.g. 8081) has no way to discover the config key. The hooks read from this field via the three-tier lookup added in WI-170, so the plumbing works — but users cannot find it without reading source code.
- **Impact**: P11 (low-friction setup) — users need to manually inspect config.json to discover customizable settings. Especially relevant for users running hamlet on a non-default port (daemon on another host, port conflict with existing service).

### SG2: `hamlet_init` uses `Path.cwd()` to determine project directory — correctness depends on MCP process spawn behavior
- **File**: `/Users/dan/code/hamlet/mcp/server.py:37`
- **Gap**: `hamlet_init` writes `.hamlet/config.json` relative to `Path.cwd()`. MCP server processes are spawned once at Claude Code startup and run persistently. The process cwd is set at spawn time and does not change as the user navigates between projects. If Claude Code does not set the MCP server's cwd to the active project root, every `hamlet_init` call initializes the wrong directory.
- **Impact**: If the cwd behavior is wrong, hamlet_init creates `.hamlet/config.json` in an unexpected location, appearing to succeed but not configuring the intended project. The failure is silent.
- **Note**: This may already work correctly if Claude Code sets the MCP server cwd to the active session's project root. Verification requires runtime testing. Promoting to significant given it cannot be confirmed from code alone and the impact is silent misconfiguration.

## Minor Gaps

### MG1: hamlet not in claude-marketplace CLAUDE.md plugin table
- **File**: `/Users/dan/code/claude-marketplace/CLAUDE.md`
- **Gap**: hamlet is registered in `marketplace.json` but absent from the CLAUDE.md plugin registry table (which lists beepboop, moodring, ideate, outpost). Stale human-readable index.
- **Recommendation**: Add hamlet entry to the table.

## Resolved

WI-172 gap (python3 PATH guard): **Fixed**.
